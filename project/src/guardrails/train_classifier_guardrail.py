#!/usr/bin/env python3
"""
Template script to train a finetunable classifier for the guardrail using Hugging Face Transformers.

Produces a model saved with model.save_pretrained() / tokenizer.save_pretrained()
that can be loaded with load_classifier_guardrail() and used in the chat pipeline
the same way as the LLM judge guardrail.

Usage:
  # From project/ directory (or repo root with PYTHONPATH=project):
  python -m src.guardrails.train_classifier_guardrail \\
    --data path/to/labeled_data.csv \\
    --output_dir models/my_guardrail \\
    [--base_model bert-base-uncased] [--text_column text --label_column label]

  Other Hugging Face models: roberta-base, distilbert-base-uncased, albert-base-v2, etc.

CSV format:
  - Preferred columns: "text" and "label".
  - Also supports common alternatives (case-insensitive), e.g. "Text"/"content"/"prompt"
    for text and "label"/"is_high_risk" for labels.

Output (Hugging Face format):
  - {output_dir}/config.json, model.safetensors, tokenizer files
  - {output_dir}/guardrail_config.json (threshold)

Then in config or code:
  type: "finetunable"
  model_path: "models/my_guardrail"
  threshold: 0.5
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Project root = project/ (parent of src/)
_PROJECT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT) not in sys.path:
    sys.path.insert(0, str(_PROJECT))

LOGGER = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Train a finetunable classifier guardrail with Hugging Face Transformers."
    )
    parser.add_argument(
        "--data",
        required=True,
        help="Path to CSV with text and label columns (0=low_risk, 1=high_risk)",
    )
    parser.add_argument(
        "--output_dir",
        required=True,
        help="Directory to save model and tokenizer (e.g. models/output_guardrail)",
    )
    parser.add_argument(
        "--base_model",
        default="bert-base-uncased",
        help="Hugging Face model id for sequence classification (default: bert-base-uncased). "
        "Any compatible model works, e.g. roberta-base, distilbert-base-uncased, albert-base-v2.",
    )
    parser.add_argument(
        "--text_column",
        default="text",
        help="CSV column name for content",
    )
    parser.add_argument(
        "--label_column",
        default="label",
        help="CSV column name for label (0=low_risk, 1=high_risk)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Default threshold for guardrail (score >= threshold -> FAIL)",
    )
    parser.add_argument(
        "--max_length",
        type=int,
        default=512,
        help="Max token length for inputs",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=8,
        help="Training batch size",
    )
    parser.add_argument(
        "--test_fraction",
        type=float,
        default=0.2,
        help="Fraction of data for validation (0 to disable)",
    )
    parser.add_argument(
        "--class_weight_high_risk",
        type=float,
        default=None,
        help="Weight for high_risk class (e.g. 1.8). If set, uses weighted cross-entropy loss.",
    )
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=5e-5,
        help="Learning rate (default: 5e-5. Use 1e-5 for DeBERTa models).",
    )
    parser.add_argument(
        "--warmup_ratio",
        type=float,
        default=0.1,
        help="Warmup ratio for learning rate scheduler (default: 0.1).",
    )
    args = parser.parse_args()

    hackathon_path = _PROJECT.parent / "hackathon.json"
    if not hackathon_path.exists():
        print(f"Required config not found: {hackathon_path}", file=sys.stderr)
        return 1
    try:
        cfg = json.loads(hackathon_path.read_text())
    except Exception as exc:
        print(f"Invalid JSON in {hackathon_path}: {exc}", file=sys.stderr)
        return 1
    if not isinstance(cfg, dict):
        print(f"{hackathon_path} must contain a JSON object", file=sys.stderr)
        return 1
    if "needs_gpu" not in cfg:
        print(f"{hackathon_path} missing required field: needs_gpu", file=sys.stderr)
        return 1
    if not isinstance(cfg["needs_gpu"], bool):
        print(f"{hackathon_path} field 'needs_gpu' must be a boolean", file=sys.stderr)
        return 1
    needs_gpu = cfg["needs_gpu"]
    # Force CPU for local runs when project config says GPU is not required.
    if not needs_gpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    try:
        import torch
        import numpy as np
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            TrainingArguments,
            Trainer,
        )
        from transformers import EvalPrediction
    except ImportError:
        print("This script requires transformers and torch.", file=sys.stderr)
        print("Install with: pip install transformers torch", file=sys.stderr)
        return 1

    try:
        import pandas as pd
    except ImportError:
        print("This script requires pandas for CSV loading.", file=sys.stderr)
        print("Install with: pip install pandas", file=sys.stderr)
        return 1

    if needs_gpu and not torch.cuda.is_available():
        print("hackathon.json requires GPU (needs_gpu=true), but CUDA is not available.", file=sys.stderr)
        return 1

    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        print(f"CUDA available. Using GPU: {gpu_name}", flush=True)
    else:
        print("CUDA not available, set needs_gpu in the hackathon.json file if you want to train on GPU. Training will run on CPU.", flush=True)

    path = Path(args.data)
    if not path.exists():
        print(f"Data file not found: {path}", file=sys.stderr)
        return 1

    def _read_csv_with_fallbacks(csv_path: Path):
        # Some datasets are encoded with cp1252/latin-1; try utf-8 first.
        read_errors = []
        for enc in ("utf-8", "cp1252", "latin-1"):
            try:
                return pd.read_csv(csv_path, encoding=enc)
            except Exception as exc:
                read_errors.append(f"{enc}: {type(exc).__name__}")
        print(
            f"Failed to read CSV {csv_path}. Tried encodings: {', '.join(read_errors)}",
            file=sys.stderr,
        )
        return None

    def _resolve_column(df_columns, preferred: str, aliases):
        # Case-insensitive column matching while preserving the actual column name.
        by_lower = {str(c).strip().lower(): c for c in df_columns}
        candidates = [preferred] + [a for a in aliases if a != preferred]
        for candidate in candidates:
            key = str(candidate).strip().lower()
            if key in by_lower:
                return by_lower[key]
        return None

    def _parse_binary_label(raw):
        if raw is None:
            raise ValueError("missing label")
        value = str(raw).strip().lower()
        if value in {"0", "false", "no", "low", "low_risk"}:
            return 0
        if value in {"1", "true", "yes", "high", "high_risk"}:
            return 1
        try:
            n = int(float(value))
            if n in (0, 1):
                return n
        except Exception:
            pass
        raise ValueError(f"unsupported label value: {raw}")

    df = _read_csv_with_fallbacks(path)
    if df is None:
        return 1

    LOGGER.info("Loaded training data | path=%s samples=%d columns=%s", path, len(df), list(df.columns))

    text_col = _resolve_column(
        df.columns,
        args.text_column,
        ["text", "Text", "content", "prompt", "message", "utterance"],
    )
    label_col = _resolve_column(
        df.columns,
        args.label_column,
        ["label", "Label", "is_high_risk", "is_risky"],
    )

    if text_col is None:
        print(
            f"Text column '{args.text_column}' not found. Columns: {list(df.columns)}",
            file=sys.stderr,
        )
        return 1
    if label_col is None:
        print(
            f"Label column '{args.label_column}' not found. Columns: {list(df.columns)}",
            file=sys.stderr,
        )
        return 1

    if text_col != args.text_column or label_col != args.label_column:
        print(
            f"Resolved columns -> text: '{text_col}', label: '{label_col}'",
            flush=True,
        )

    texts = df[text_col].fillna("").astype(str).tolist()
    try:
        labels = [int(_parse_binary_label(v)) for v in df[label_col].tolist()]
    except ValueError as exc:
        print(f"Invalid label values in column '{label_col}': {exc}", file=sys.stderr)
        return 1
    if set(labels) - {0, 1}:
        print("Labels should be 0 (low_risk) and 1 (high_risk). Found:", sorted(set(labels)), file=sys.stderr)
        return 1

    label_counts = {0: labels.count(0), 1: labels.count(1)}
    LOGGER.info(
        "Label distribution | low_risk=%d (%.1f%%) high_risk=%d (%.1f%%)",
        label_counts[0],
        100 * label_counts[0] / len(labels),
        label_counts[1],
        100 * label_counts[1] / len(labels),
    )
    print(f"Using base model: {args.base_model}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model,
        num_labels=2,
        id2label={0: "low_risk", 1: "high_risk"},
        label2id={"low_risk": 0, "high_risk": 1},
    )

    enc = tokenizer(
        texts,
        truncation=True,
        max_length=args.max_length,
        padding="max_length",
        return_tensors="pt",
    )

    class SimpleDataset(torch.utils.data.Dataset):
        def __init__(self, input_ids, attention_mask, labels):
            self.input_ids = input_ids
            self.attention_mask = attention_mask
            self.labels = torch.tensor(labels, dtype=torch.long)

        def __len__(self):
            return len(self.labels)

        def __getitem__(self, i):
            return {
                "input_ids": self.input_ids[i],
                "attention_mask": self.attention_mask[i],
                "labels": self.labels[i],
            }

    full_dataset = SimpleDataset(enc["input_ids"], enc["attention_mask"], labels)

    if args.test_fraction > 0:
        n = len(full_dataset)
        indices = torch.randperm(n, generator=torch.Generator().manual_seed(42))
        n_test = int(n * args.test_fraction)
        train_idx, eval_idx = indices[n_test:], indices[:n_test]
        train_dataset = torch.utils.data.Subset(full_dataset, train_idx.tolist())
        eval_dataset = torch.utils.data.Subset(full_dataset, eval_idx.tolist())
        LOGGER.info("Data split | train=%d eval=%d", len(train_dataset), len(eval_dataset))
    else:
        train_dataset = full_dataset
        eval_dataset = None
        LOGGER.info("Data split | train=%d eval=0 (no validation)", len(train_dataset))

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        warmup_ratio=args.warmup_ratio,
        weight_decay=0.01,
        max_grad_norm=1.0,
        fp16=False,
        eval_strategy="epoch" if eval_dataset else "no",
        save_strategy="epoch",
        load_best_model_at_end=bool(eval_dataset),
        metric_for_best_model="f1" if eval_dataset else None,
        greater_is_better=True if eval_dataset else None,
    )

    def compute_metrics(eval_pred: EvalPrediction):
        from sklearn.metrics import f1_score, precision_score, recall_score
        preds = np.argmax(eval_pred.predictions, axis=1)
        acc = (preds == eval_pred.label_ids).mean()
        f1 = f1_score(eval_pred.label_ids, preds, zero_division=0.0)
        prec = precision_score(eval_pred.label_ids, preds, zero_division=0.0)
        rec = recall_score(eval_pred.label_ids, preds, zero_division=0.0)
        return {"accuracy": acc, "f1": f1, "precision": prec, "recall": rec}

    # Weighted trainer for class imbalance
    if args.class_weight_high_risk is not None:
        class_weights = torch.tensor(
            [1.0, args.class_weight_high_risk],
            dtype=torch.float32,
        ).to("cuda" if torch.cuda.is_available() else "cpu")
        LOGGER.info("Using class-weighted loss | low_risk=1.0 high_risk=%.2f", args.class_weight_high_risk)

        class WeightedTrainer(Trainer):
            def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
                labels = inputs.pop("labels")
                outputs = model(**inputs)
                logits = outputs.logits
                loss = torch.nn.functional.cross_entropy(logits, labels, weight=class_weights)
                return (loss, outputs) if return_outputs else loss

        trainer = WeightedTrainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            compute_metrics=compute_metrics if eval_dataset else None,
        )
    else:
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            compute_metrics=compute_metrics if eval_dataset else None,
        )

    LOGGER.info(
        "Training started | model=%s epochs=%d batch_size=%d output_dir=%s",
        args.base_model,
        args.epochs,
        args.batch_size,
        args.output_dir,
    )
    trainer.train()
    LOGGER.info("Training complete")

    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    LOGGER.info("Model and tokenizer saved to %s", args.output_dir)

    guardrail_config = {
        "threshold": args.threshold,
    }
    config_path = Path(args.output_dir) / "guardrail_config.json"
    with open(config_path, "w") as f:
        json.dump(guardrail_config, f, indent=2)
    LOGGER.info("Guardrail config saved | path=%s threshold=%.4f", config_path, args.threshold)
    print(f"Saved guardrail config to {config_path}")

    print("\nTo use this guardrail:")
    print(f"  1. In YAML: type: \"finetunable\", model_path: \"{args.output_dir}\"")
    print("  2. In code: load_classifier_guardrail(model_path=..., name=..., description=..., threshold=...)")
    print("  3. Use as input/output guardrail in your runtime or evaluator")
    return 0


if __name__ == "__main__":
    sys.exit(main())

import argparse
import time

from src.preprocess import run_preprocessing
from src.train import run_training


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run Texas COVID preprocessing "
            "and modeling end-to-end."
        )
    )
    parser.add_argument(
        "--skip-preprocess",
        action="store_true",
        help="Use existing data/processed files.",
    )
    parser.add_argument(
        "--skip-train",
        action="store_true",
        help="Run preprocessing only.",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help=(
            "Do not download raw files. "
            "Expect data/raw to be populated."
        ),
    )
    args = parser.parse_args()

    start = time.time()

    if not args.skip_preprocess:
        run_preprocessing(
            download=not args.no_download
        )

    if not args.skip_train:
        run_training()

    elapsed = time.time() - start
    print(
        f"\nPipeline completed in "
        f"{elapsed / 60:.1f} minutes."
    )
    print(
        "Open the dashboard with:\n"
        "  streamlit run app.py"
    )


if __name__ == "__main__":
    main()

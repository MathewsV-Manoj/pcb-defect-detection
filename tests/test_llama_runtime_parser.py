import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "llm_advisory"))

from run_executorch import (  # noqa: E402
    observer_tokens_per_second,
    observer_ttft_ms,
    parse_pytorch_observer,
)


class ExecuTorchTelemetryTests(unittest.TestCase):
    def test_parses_observer_and_calculates_ttft_and_generation_rate(self):
        output = (
            "some runner log\n"
            'PyTorchObserver {"prompt_tokens":20,"generated_tokens":10,'
            '"inference_start_ms":1000,"first_token_ms":1150,'
            '"prompt_eval_end_ms":1300,"inference_end_ms":1700,'
            '"SCALING_FACTOR_UNITS_PER_SECOND":1000}\n'
        )
        stats = parse_pytorch_observer(output)
        self.assertIsNotNone(stats)
        self.assertEqual(observer_ttft_ms(stats), 150.0)
        self.assertEqual(observer_tokens_per_second(stats), 25.0)

    def test_missing_or_invalid_observer_keeps_metrics_unavailable(self):
        self.assertIsNone(parse_pytorch_observer("runner output without stats"))
        self.assertIsNone(parse_pytorch_observer("PyTorchObserver not-json"))
        self.assertIsNone(observer_ttft_ms(None))
        self.assertIsNone(observer_tokens_per_second(None))

    def test_invalid_or_zero_duration_stats_do_not_create_fake_rates(self):
        stats = {
            "generated_tokens": 0,
            "inference_start_ms": 100,
            "first_token_ms": 90,
            "prompt_eval_end_ms": 100,
            "inference_end_ms": 100,
        }
        self.assertIsNone(observer_ttft_ms(stats))
        self.assertIsNone(observer_tokens_per_second(stats))


if __name__ == "__main__":
    unittest.main()

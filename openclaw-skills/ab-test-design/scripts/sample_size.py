#!/usr/bin/env python3
"""Sample size and duration for an A/B test. Standard library only.

Conversion metric (baseline rate, relative effect):
  python3 sample_size.py --baseline 0.12 --mde 0.10 --daily-users 3000

Continuous metric (standard deviation, absolute effect):
  python3 sample_size.py --std 40 --mde-abs 3 --daily-users 3000

--mde is relative to the baseline rate or mean (0.10 = +10 %).
--mde-abs is absolute (0.01 = +1 percentage point for a rate, metric units for a mean).
The test is two-sided. With more than two variants, alpha is Bonferroni-corrected
for the comparisons against control.
"""
import argparse
import math
from statistics import NormalDist


def sample_size_per_variant(alpha, power, delta, baseline=None, std=None):
    """Users per variant for a two-sided z-test detecting a difference of `delta`."""
    z_alpha = NormalDist().inv_cdf(1 - alpha / 2)
    z_power = NormalDist().inv_cdf(power)
    if std is not None:
        variance_sum = 2 * std ** 2
    else:
        treated = baseline + delta
        if not 0 < treated < 1:
            raise ValueError("baseline + effect must stay between 0 and 1")
        variance_sum = baseline * (1 - baseline) + treated * (1 - treated)
    return math.ceil((z_alpha + z_power) ** 2 * variance_sum / delta ** 2)


def run_length(total_users, daily_users):
    """Days of traffic needed, and the run length rounded up to whole weeks."""
    days = math.ceil(total_users / daily_users)
    return days, max(1, math.ceil(days / 7)) * 7


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    metric = parser.add_mutually_exclusive_group(required=True)
    metric.add_argument("--baseline", type=float, help="baseline conversion rate, e.g. 0.12")
    metric.add_argument("--std", type=float, help="standard deviation of a continuous metric")
    effect = parser.add_mutually_exclusive_group(required=True)
    effect.add_argument("--mde", type=float, help="minimum detectable effect, relative (0.10 = +10%%)")
    effect.add_argument("--mde-abs", type=float, help="minimum detectable effect, absolute")
    parser.add_argument("--mean", type=float, help="baseline mean; needed with --std and --mde")
    parser.add_argument("--alpha", type=float, default=0.05, help="two-sided significance level (default 0.05)")
    parser.add_argument("--power", type=float, default=0.80, help="statistical power (default 0.80)")
    parser.add_argument("--variants", type=int, default=2, help="variants including control (default 2)")
    parser.add_argument("--daily-users", type=float, help="eligible users entering the test per day, all variants")
    args = parser.parse_args(argv)

    if args.variants < 2:
        parser.error("--variants must be at least 2")
    if args.baseline is not None and not 0 < args.baseline < 1:
        parser.error("--baseline must be between 0 and 1")
    if args.mde_abs is not None:
        delta = args.mde_abs
    elif args.std is not None:
        if args.mean is None:
            parser.error("--mde with --std needs --mean (or use --mde-abs)")
        delta = args.mde * args.mean
    else:
        delta = args.mde * args.baseline
    if delta <= 0:
        parser.error("the effect to detect must be positive")

    alpha = args.alpha / (args.variants - 1)
    try:
        per_variant = sample_size_per_variant(alpha, args.power, delta, baseline=args.baseline, std=args.std)
    except ValueError as error:
        parser.error(str(error))
    total = per_variant * args.variants

    if args.baseline is not None:
        print(f"Effect to detect:  {args.baseline:.2%} -> {args.baseline + delta:.2%} "
              f"({delta * 100:+.2f} pp, {delta / args.baseline:+.1%} relative)")
    else:
        print(f"Effect to detect:  {delta:+g} (standard deviation {args.std:g})")
    correction = f", Bonferroni {alpha:.4g} per comparison" if args.variants > 2 else ""
    print(f"Alpha / power:     {args.alpha:g} two-sided{correction} / {args.power:.0%}")
    print(f"Users per variant: {per_variant:,}")
    print(f"Total users:       {total:,} ({args.variants} variants)")
    if args.daily_users:
        days, run = run_length(total, args.daily_users)
        weeks = run // 7
        print(f"Duration:          {days} days of traffic -> run {run} days ({weeks} full week{'s' if weeks > 1 else ''})")
        if run > 56:
            print("Warning: more than 8 weeks. Consider a larger MDE, a more sensitive metric, "
                  "a wider eligible population, or not running this as an A/B test.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Query the local Prometheus instance for CO2 sensor metrics."""

import argparse
import datetime
import json
import sys
import urllib.request
import urllib.parse

BASE_URL = "http://prometheus.smithpeople.org"


def query_range(metric, hours=24, step=300):
    end = int(datetime.datetime.now().timestamp())
    start = end - hours * 3600
    params = urllib.parse.urlencode({
        "query": metric,
        "start": start,
        "end": end,
        "step": step,
    })
    url = f"{BASE_URL}/api/v1/query_range?{params}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.load(resp)


def query_instant(metric):
    params = urllib.parse.urlencode({"query": metric})
    url = f"{BASE_URL}/api/v1/query?{params}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.load(resp)


def list_metrics(filter_str=None):
    url = f"{BASE_URL}/api/v1/label/__name__/values"
    with urllib.request.urlopen(url, timeout=10) as resp:
        d = json.load(resp)
    names = d["data"]
    if filter_str:
        names = [n for n in names if filter_str.lower() in n.lower()]
    return names


def fmt_ts(ts):
    return datetime.datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M")


def print_range_result(data, label=None):
    results = data["data"]["result"]
    if not results:
        print("No data returned.")
        return
    for series in results:
        metric_labels = {k: v for k, v in series["metric"].items() if k != "__name__"}
        header = label or series["metric"].get("__name__", "metric")
        if metric_labels:
            header += " " + str(metric_labels)
        vals = series["values"]
        floats = [float(v) for _, v in vals]
        first_ts, first_v = vals[0]
        last_ts, last_v = vals[-1]
        print(f"=== {header} ===")
        print(f"  Points : {len(vals)}")
        print(f"  First  : {float(first_v):>10.0f}  @ {fmt_ts(first_ts)}")
        print(f"  Last   : {float(last_v):>10.0f}  @ {fmt_ts(last_ts)}")
        print(f"  Min    : {min(floats):>10.0f}")
        print(f"  Max    : {max(floats):>10.0f}")
        print(f"  Delta  : {float(last_v) - float(first_v):>+10.0f}")
        print()
        print(f"  {'Timestamp':<17} {'Value':>10}")
        print(f"  {'-'*17} {'-'*10}")
        for ts, v in vals:
            print(f"  {fmt_ts(ts):<17} {float(v):>10.0f}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Query Prometheus for CO2 sensor metrics")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List available metrics")
    p_list.add_argument("filter", nargs="?", help="Filter string")

    p_mem = sub.add_parser("memory", help="Show free memory over time")
    p_mem.add_argument("--hours", type=int, default=24)
    p_mem.add_argument("--step", type=int, default=300, help="Step in seconds")

    p_co2 = sub.add_parser("co2", help="Show CO2 readings over time")
    p_co2.add_argument("--hours", type=int, default=24)
    p_co2.add_argument("--step", type=int, default=300)

    p_query = sub.add_parser("query", help="Raw range query")
    p_query.add_argument("metric")
    p_query.add_argument("--hours", type=int, default=24)
    p_query.add_argument("--step", type=int, default=300)

    args = parser.parse_args()

    if args.cmd == "list":
        for name in list_metrics(args.filter):
            print(name)

    elif args.cmd == "memory":
        data = query_range("mqtt_consumer_free_memory", hours=args.hours, step=args.step)
        print_range_result(data, label="free_memory (bytes)")

    elif args.cmd == "co2":
        data = query_range("mqtt_consumer_co2", hours=args.hours, step=args.step)
        print_range_result(data, label="co2 (ppm)")

    elif args.cmd == "query":
        data = query_range(args.metric, hours=args.hours, step=args.step)
        print_range_result(data)


if __name__ == "__main__":
    main()

import os
from dataclasses import dataclass
from pathlib import Path
import re
from typing import List

from tabulate import tabulate


@dataclass
class Result:
    run_name: str
    scene_name: str
    resolution: str
    rendertime_seconds: float
    max_queue_size: int
    spp: int
    estimated_bytes_of_one_sample_in_all_queues: int
    real_bytes_of_one_sample_in_all_queues: int
    device: str


@dataclass
class RunResult:
    results: List[Result]

    def select(self, scene_name: str, resolution: str) -> Result:
        for result in self.results:
            if result.scene_name == scene_name and result.resolution == resolution:
                return result


def parse_log_file(run_name: str, scene_name: str, log_file: Path):
    render_time_pattern = re.compile(r"Total rendering time: ((\d+)\.(\d+))")
    max_queue_size_pattern = re.compile(r"maxQueueSize (\d+)")
    estimated_bytes_of_one_sample_in_all_queues_pattern = re.compile(
        r"bytesOfOneSampleInAllQueues (\d+)"
    )
    real_bytes_of_one_sample_in_all_queues_pattern = re.compile(
        r"bytes per accumulated queue entry is (\d+)"
    )
    device_pattern = re.compile(r"CUDA device 0 \((.+)\) ")

    resolution = "fullhd"
    if "4k" in log_file.stem:
        resolution = "4k"

    render_time = None
    max_queue_size = None
    estimated_bytes_of_one_sample_in_all_queues = None
    real_bytes_of_one_sample_in_all_queues = None
    device = None

    with open(log_file, "r") as f:
        for line in f.readlines():
            render_time_match = re.search(render_time_pattern, line)
            if render_time_match:
                render_time = float(render_time_match.groups()[0])

            max_queue_size_match = re.search(max_queue_size_pattern, line)
            if max_queue_size_match:
                max_queue_size = int(max_queue_size_match.groups()[0])

            estimated_bytes_of_one_sample_in_all_queues_match = re.search(
                estimated_bytes_of_one_sample_in_all_queues_pattern, line
            )
            if estimated_bytes_of_one_sample_in_all_queues_match:
                estimated_bytes_of_one_sample_in_all_queues = int(
                    estimated_bytes_of_one_sample_in_all_queues_match.groups()[0]
                )

            real_bytes_of_one_sample_in_all_queues_match = re.search(
                real_bytes_of_one_sample_in_all_queues_pattern, line
            )
            if real_bytes_of_one_sample_in_all_queues_match:
                real_bytes_of_one_sample_in_all_queues = int(
                    real_bytes_of_one_sample_in_all_queues_match.groups()[0]
                )

            device_pattern_match = re.search(device_pattern, line)
            if device_pattern_match:
                device = device_pattern_match.groups()[0]

    return Result(
        run_name=run_name,
        scene_name=scene_name,
        resolution=resolution,
        spp=16,
        rendertime_seconds=render_time,
        max_queue_size=max_queue_size,
        estimated_bytes_of_one_sample_in_all_queues=estimated_bytes_of_one_sample_in_all_queues,
        real_bytes_of_one_sample_in_all_queues=real_bytes_of_one_sample_in_all_queues,
        device=device,
    )


def parse_folder(folder: Path) -> RunResult:
    run_name = folder.stem
    results = []

    for scene_name in os.listdir(folder):
        for result_file in os.listdir(folder / scene_name):
            result_file = Path(result_file)
            if result_file.suffix == ".txt":
                result = parse_log_file(
                    run_name, scene_name, folder / scene_name / result_file
                )
                results.append(result)

    return RunResult(results)


class Report:
    def __init__(
        self,
        scene_names: List[str],
        resolutions: List[str],
        baseline_run: RunResult,
        improved_run: RunResult,
    ):
        self.scene_names = scene_names
        self.resolutions = resolutions
        self.rows = []
        for scene_name in scene_names:
            for resolution in resolutions:
                self.rows.append([f"{scene_name} {resolution}"])
        self.headers = ["Scene Name"]
        self.baseline_run = baseline_run
        self.improved_run = improved_run

    def generate(self):
        self.append_scalar(
            "estimated size", "estimated_bytes_of_one_sample_in_all_queues"
        )
        self.append_scalar("real size", "real_bytes_of_one_sample_in_all_queues")
        self.append_difference("max queue size", "max_queue_size")
        self.append_difference("render time", "rendertime_seconds")

    def append_scalar(self, display_name: str, attr_name: str):
        i = 0
        self.headers.append(f"{display_name}")
        for scene_name in self.scene_names:
            for resolution in self.resolutions:
                old = getattr(
                    self.baseline_run.select(scene_name, resolution), attr_name
                )
                self.rows[i].append(old)
                i += 1

    def append_difference(
        self,
        display_name: str,
        attr_name: str,
    ):
        i = 0
        self.headers.append(f"{display_name} baseline")
        self.headers.append(f"{display_name} improved")
        self.headers.append(f"improvement %")
        for scene_name in self.scene_names:
            for resolution in self.resolutions:
                old = getattr(
                    self.baseline_run.select(scene_name, resolution), attr_name
                )
                self.rows[i].append(old)
                new = getattr(
                    self.improved_run.select(scene_name, resolution), attr_name
                )
                self.rows[i].append(new)
                if old is not None and new is not None:
                    self.rows[i].append(round((old - new) / old * 100, 2))
                else:
                    self.rows[i].append(None)
                i += 1


def collect_scene_names(run_results: List[RunResult]) -> List[str]:
    scene_names = set()
    for run_result in run_results:
        for result in run_result.results:
            scene_names.add(result.scene_name)
    return list(sorted(scene_names))


def collect_resolutions(run_results: List[RunResult]) -> List[str]:
    resolutions = set()
    for run_result in run_results:
        for result in run_result.results:
            resolutions.add(result.resolution)
    return list(sorted(resolutions))


def main():
    root = Path(__file__).parent
    baseline_folder = Path(root / "benchmark-baseline-3080")
    improved_folder = Path(root / "benchmark-improved-3080")

    baseline_run_result = parse_folder(baseline_folder)
    improved_run_result = parse_folder(improved_folder)

    scene_names = collect_scene_names([baseline_run_result, improved_run_result])
    resolutions = collect_resolutions([baseline_run_result, improved_run_result])

    report = Report(scene_names, resolutions, baseline_run_result, improved_run_result)
    report.generate()
    print(tabulate(report.rows, headers=report.headers))


if __name__ == "__main__":
    main()

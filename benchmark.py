import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List


@dataclass
class Scene:
    name: str
    file_basename: str
    spp_override: Optional[int] = None


scenes: List[Scene] = [
    Scene(
        "pbrt-book",
        "book",
    ),
    Scene("landscape", "view-0"),
    Scene("watercolor", "camera-1", 256),
    Scene("disney-cloud", "disney-cloud", 256),
]


def call_pbrt(
    pbrt_exe: Path,
    scene_path: Path,
    log_path: Path,
    exr_path: Path,
    spp: int,
    use_gpu: bool,
):
    command = [
        pbrt_exe,
        str(scene_path),
        "--log-level",
        "verbose",
        "--wavefront",
        "--spp",
        str(spp),
        "--outfile",
        str(exr_path),
    ]
    if use_gpu:
        command.append("--gpu")

    print(command)

    with open(log_path, "w") as f:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )

        for line in process.stdout:
            print(line, end="")
            f.write(line)

        process.wait()


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "target_folder",
        type=str,
    )

    parser.add_argument(
        "pbrt_exe",
        type=str,
    )

    parser.add_argument("--use-cpu", action="store_true", default=False)

    return parser.parse_args()


def main():
    args = parse_args()
    root_folder = Path(__file__).parent
    target_folder = Path(args.target_folder)
    for scene in scenes:
        for resolution in ["fullhd", "4k"]:
            scene_path = (
                root_folder / scene.name / f"{scene.file_basename}_{resolution}.pbrt"
            )
            log_path = (
                target_folder / scene.name / f"{scene.file_basename}_{resolution}.txt"
            )
            exr_path = (
                target_folder / scene.name / f"{scene.file_basename}_{resolution}.exr"
            )

            exr_path.parent.mkdir(parents=True, exist_ok=True)

            call_pbrt(
                args.pbrt_exe,
                scene_path,
                log_path,
                exr_path,
                scene.spp_override if scene.spp_override else 1024,
                use_gpu=not args.use_cpu,
            )


if __name__ == "__main__":
    main()

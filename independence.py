import argparse
import glob
import os
import sys
import subprocess
import tempfile
import shutil
from collections import defaultdict

VENV_PATH = []

def python_cmd(cmd):
    return [os.path.join(VENV_PATH[0], "bin", "python")] + cmd

def pip_cmd(cmd):
    return [os.path.join(VENV_PATH[0], "bin", "python"), "-m", "pip"] + cmd


def download_package_targz(packages, outdir):
    for pkg in packages:
        subprocess.run(pip_cmd(["download", "--no-binary=:all:", "--dest", outdir, pkg]), check=True)
        archives = glob.glob(os.path.join(outdir, "*.tar*"))
        for archive in archives:
            shutil.unpack_archive(archive, extract_dir=outdir)

def get_all_files_per_package():
    result = subprocess.run(pip_cmd(["freeze"]), capture_output=True, text=True, check=True)
    packages = {line.split("==")[0] for line in result.stdout.strip().split("\n")}
    files_per_package = defaultdict(list)

    for package in packages:
        result = subprocess.run(pip_cmd(["show", "-f", package]), capture_output=True, text=True, check=True)
        for line in result.stdout.splitlines():
            if line.startswith("  "):
                filename = line.strip()
                files_per_package[package].append(filename)
    return files_per_package

def download_package_and_dependencies(package_name):
    subprocess.run([sys.executable, "-m", "venv", VENV_PATH[0]], check=True)
    subprocess.run(pip_cmd(["install", "--no-binary=:all:", package_name]), check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("package")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as temp_env:
        VENV_PATH.append(os.path.join(temp_env, "venv"))
        download_package_and_dependencies(args.package)

        out = subprocess.run(python_cmd(["-c", "import site; print(site.getsitepackages()[0])"]), capture_output=True, text=True, check=True)
        site_packages = out.stdout.strip()
        locs_per_package: dict[str, int] = defaultdict(int)
        binary_files_per_package = defaultdict(list)
        for package, files in get_all_files_per_package().items():
            for file in files:
                file_path = os.path.join(site_packages, file)
                if file_path.endswith(".py"):
                    with open(file_path, "r") as f:
                        code_lines = total_lines = 0
                        for line in f:
                            line = line.strip()
                            if len(line) and not line.startswith("#"):
                                code_lines += 1
                            total_lines += 1
                        locs_per_package[package] += code_lines
                elif file_path.endswith(".so"):
                    binary_files_per_package[package].append((file, os.path.getsize(file_path)))


        print("\n\n\nLOCs per package:")
        for package, locs in sorted(locs_per_package.items(), key=lambda x: x[1], reverse=True):
            print(f"{package:.<30} {locs}")

        print("\n\n\nBinary size of shared libs per package:")
        for package, files in binary_files_per_package.items():
            for file, size in files:
                print(f"{package:<30} {file:<80} {size:>10}B")
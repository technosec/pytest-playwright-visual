import base64
import json
import sys
import os
import shutil
from io import BytesIO
from pathlib import Path
from typing import Any, Callable
import pytest
from PIL import Image
from pixelmatch.contrib.PIL import pixelmatch
import allure


@pytest.fixture
def assert_snapshot(pytestconfig: Any, request: Any, browser_name: str, rovalab_page ) -> Callable:
    test_name = f"{str(Path(request.node.name))}[{str(sys.platform)}]"
    test_dir = str(Path(request.node.name)).split('[', 1)[0]

    def compare(img: bytes, rovalab_page, *, threshold: float = 0.3, fail_fast=False) -> None:
        name=f'{test_name}[{rovalab_page.current_tab}].png'
        update_snapshot = pytestconfig.getoption("--update-snapshots")
        test_file_name = str(os.path.basename(Path(request.node.fspath))).strip('.py')
        filepath = (
                Path(request.node.fspath).parent.resolve()
                / 'snapshots'
                / test_file_name
                / test_dir
        )
        filepath.mkdir(parents=True, exist_ok=True)
        file = filepath / name
        # Create a dir where all snapshot test failures will go
        results_dir_name = (Path(request.node.fspath).parent.resolve()
                            / "snapshot_tests_failures")
        test_results_dir = (results_dir_name
                            / test_file_name / test_name)
        # Remove a single test's past run dir with actual, diff and expected images
        if test_results_dir.exists():
            shutil.rmtree(test_results_dir)
        if update_snapshot:
            file.write_bytes(img)
            print("--> Snapshots updated. Please review images")
            return
        if not file.exists():
            file.write_bytes(img)
            print("--> New snapshot(s) created. Please review images")
            return
        img_a = Image.open(BytesIO(img))
        img_b = Image.open(file)
        img_diff = Image.new("RGBA", img_a.size)
        mismatch = pixelmatch(img_a, img_b, img_diff, threshold=threshold, fail_fast=fail_fast)
        if mismatch == 0:
            return
        else:

             
            # Create new test_results folder
            test_results_dir.mkdir(parents=True, exist_ok=True)
            img_diff.save(f'{test_results_dir}/Diff_{name}')
            img_a.save(f'{test_results_dir}/Actual_{name}')
            img_b.save(f'{test_results_dir}/Expected_{name}')

            # Read the three files and encode to base64
            expected = base64.b64encode(Path(f'{test_results_dir}/Expected_{name}').read_bytes()).decode()
            actual = base64.b64encode(Path(f'{test_results_dir}/Actual_{name}').read_bytes()).decode()
            diff = base64.b64encode(Path(f'{test_results_dir}/Diff_{name}').read_bytes()).decode()

            # Wrap in a JSON, encode as bytes
            content = json.dumps({
                'expected': f'data:image/png;base64,{expected}',
                'actual': f'data:image/png;base64,{actual}',
                'diff': f'data:image/png;base64,{diff}',
            }).encode()

            # Attach to the test report
            allure.attach(content,
                        name='Screenshot diff',
                        attachment_type='application/vnd.allure.image.diff')
            
            # allure.attach.file(f'{test_results_dir}/Diff_{name}', name='Diff Image',
            #             attachment_type=allure.attachment_type.PNG)
            # allure.attach.file(f'{test_results_dir}/Actual_{name}', name='Actual Image',
            #                     attachment_type=allure.attachment_type.PNG)
            # allure.attach.file(f'{test_results_dir}/Expected_{name}', name='Expected Image',
            #                     attachment_type=allure.attachment_type.PNG)
            pytest.fail("--> Snapshots DO NOT match!")

    return compare


def pytest_addoption(parser: Any) -> None:
    group = parser.getgroup("playwright-snapshot", "Playwright Snapshot")
    group.addoption(
        "--update-snapshots",
        action="store_true",
        default=False,
        help="Update snapshots.",
    )

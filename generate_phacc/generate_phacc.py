#! /usr/bin/env python

import pathlib
import re
import shutil
import os

import click
import git

from ha import prepare_homeassistant
from const import (
    TMP_DIR,
    PACKAGE_DIR,
    REQUIREMENTS_FILE,
    CONST_FILE,
    REQUIREMENTS_FILE_DEV,
    LICENSE_FILE_HA,
    LICENSE_FILE_NEW,
    path,
    files,
    requirements_remove,
    HA_VERSION_FILE,
)

@click.command
@click.option("--regen/--no-regen", default=False, help="Whether to regenerate despite version")
def cli(regen):
    if os.path.isdir(PACKAGE_DIR):
        shutil.rmtree(PACKAGE_DIR)
    if os.path.isfile(REQUIREMENTS_FILE):
        os.remove(REQUIREMENTS_FILE)

    ha_version = prepare_homeassistant()

    with open(HA_VERSION_FILE, "r") as f:
        current_version = f.read()
    print(f"Current Version: {current_version}")


    def process_files():
        os.mkdir(PACKAGE_DIR)
        os.mkdir(os.path.join(PACKAGE_DIR, "test_util"))
        os.makedirs(os.path.join(PACKAGE_DIR, "components", "recorder"))
        os.makedirs(os.path.join(PACKAGE_DIR, "components", "diagnostics"))
        os.makedirs(os.path.join(PACKAGE_DIR, "testing_config", "custom_components", "test_constant_deprecation"))
        shutil.copy2(os.path.join(TMP_DIR, REQUIREMENTS_FILE), REQUIREMENTS_FILE)
        shutil.copy2(
            os.path.join(TMP_DIR, "homeassistant", CONST_FILE),
            os.path.join(PACKAGE_DIR, CONST_FILE),
        )
        shutil.copy2(
            os.path.join(TMP_DIR, "tests", "test_util", "aiohttp.py"),
            os.path.join(PACKAGE_DIR, "test_util", "aiohttp.py"),
        )
        shutil.copy2(
            os.path.join(TMP_DIR, "tests", "test_util", "__init__.py"),
            os.path.join(PACKAGE_DIR, "test_util", "__init__.py"),
        )
        shutil.copy2(
            os.path.join(TMP_DIR, "tests", "components", "recorder", "common.py"),
            os.path.join(PACKAGE_DIR, "components", "recorder", "common.py"),
        )
        shutil.copy2(
            os.path.join(TMP_DIR, "tests", "components", "recorder", "db_schema_0.py"),
            os.path.join(PACKAGE_DIR, "components", "recorder", "db_schema_0.py"),
        )
        shutil.copy2(
            os.path.join(TMP_DIR, "tests", "components", "recorder", "__init__.py"),
            os.path.join(PACKAGE_DIR, "components", "recorder", "__init__.py"),
        )
        shutil.copy2(
            os.path.join(TMP_DIR, "tests", "components", "diagnostics", "__init__.py"),
            os.path.join(PACKAGE_DIR, "components", "diagnostics", "__init__.py"),
        )
        shutil.copy2(
            os.path.join(TMP_DIR, "tests", "components", "__init__.py"),
            os.path.join(PACKAGE_DIR, "components", "__init__.py"),
        )
        shutil.copy2(
            os.path.join(TMP_DIR, "tests", "testing_config", "__init__.py"),
            os.path.join(PACKAGE_DIR, "testing_config", "__init__.py"),
        )
        shutil.copy2(
            os.path.join(TMP_DIR, "tests", "testing_config", "custom_components", "__init__.py"),
            os.path.join(PACKAGE_DIR, "testing_config", "custom_components", "__init__.py"),
        )
        shutil.copy2(
            os.path.join(TMP_DIR, "tests", "testing_config", "custom_components", "test_constant_deprecation", "__init__.py"),
            os.path.join(PACKAGE_DIR, "testing_config", "custom_components", "test_constant_deprecation", "__init__.py"),
        )
        shutil.copy2(
            os.path.join(TMP_DIR, LICENSE_FILE_HA),
            LICENSE_FILE_NEW,
        )

        for f in files:
            shutil.copy2(os.path.join(TMP_DIR, "tests", f), os.path.join(PACKAGE_DIR, f))

            filename = os.path.join(PACKAGE_DIR, f)

            with open(filename, "r") as file:
                filedata = file.read()

            filedata = filedata.replace(
                "tests.", "." * (f.count("/") + 1)
            )  # Add dots depending on depth

            with open(filename, "w") as file:
                file.write(filedata)

        os.rename(
            os.path.join(PACKAGE_DIR, "conftest.py"),
            os.path.join(PACKAGE_DIR, "plugins.py"),
        )

        with open(os.path.join(PACKAGE_DIR, CONST_FILE), "r") as original_file:
            data = original_file.readlines()
        new_data = [d for d in data[:100] if "version" in d.lower() or "from typing" in d]
        new_data.insert(0, data[0])

        with open(os.path.join(PACKAGE_DIR, CONST_FILE), "w") as new_file:
            new_file.write("".join(new_data))

        added_text = "This file is originally from homeassistant/core and modified by pytest-homeassistant-custom-component.\n"
        triple_quote = '"""\n'

        for f in pathlib.Path(PACKAGE_DIR).rglob("*.py"):
            with open(f, "r") as original_file:
                data = original_file.readlines()

            multiline_docstring = not data[0].endswith(triple_quote)
            line_after_docstring = 1
            old_docstring = ""
            if not multiline_docstring:
                old_docstring = data[0][3:][:-4]
            else:
                old_docstring = data[0][3:]
                while data[line_after_docstring] != triple_quote:
                    old_docstring += data[line_after_docstring]
                    line_after_docstring += 1
                line_after_docstring += 1  # Skip last triplequote

            new_docstring = f"{triple_quote}{old_docstring}\n\n{added_text}{triple_quote}"
            body = "".join(data[line_after_docstring:])
            with open(f, "w") as new_file:
                new_file.write("".join([new_docstring, body]))

        added_text = "# This file is originally from homeassistant/core and modified by pytest-homeassistant-custom-component.\n"

        with open(REQUIREMENTS_FILE, "r") as original_file:
            data = original_file.readlines()

        def is_test_requirement(requirement):
            # if ==  not in d this is either a comment or unkown package, include
            if "==" not in requirement:
                return True

            regex = re.compile("types-.+")
            if re.match(regex, requirement):
                return False

            if d.split("==")[0] in requirements_remove:
                return False

            return True

        new_data = []
        removed_data = []
        for d in data:
            if is_test_requirement(d):
                new_data.append(d)
            else:
                removed_data.append(d)
        new_data.append(f"homeassistant=={ha_version}\n")
        new_data.insert(0, added_text)

        def find_dependency(dependency, data):
            for d in data:
                if dependency in d.lower():
                    return d
            raise ValueError(f"could not find {dependency}")

        with open(os.path.join(TMP_DIR, "requirements_all.txt"), "r") as f:
            data = f.readlines()

        def add_dependency(dependency, ha_data, new_data):
            dep = find_dependency(dependency, data)
            if not "\n" == dep[-2:]:
                dep = f"{dep}\n"
            new_data.append(dep)

        add_dependency("sqlalchemy", data, new_data)
        add_dependency("paho-mqtt", data, new_data)
        add_dependency("numpy", data, new_data)

        removed_data.insert(0, added_text)

        with open(REQUIREMENTS_FILE, "w") as new_file:
            new_file.writelines(new_data)

        with open(REQUIREMENTS_FILE_DEV, "w") as new_file:
            new_file.writelines(removed_data)

        from pytest_homeassistant_custom_component.const import __version__

        with open("README.md", "r") as original_file:
            data = original_file.readlines()

        data[
            2
        ] = f"![HA core version](https://img.shields.io/static/v1?label=HA+core+version&message={__version__}&labelColor=blue)\n"

        with open("README.md", "w") as new_file:
            new_file.write("".join(data))

        print(f"New Version: {__version__}")

        # modify load_fixture
        with open(os.path.join(PACKAGE_DIR, "common.py"), "r") as original_file:
            data = original_file.readlines()

        import_time_lineno = [i for i, line in enumerate(data) if "import time" in line]
        assert len(import_time_lineno) == 1
        data.insert(import_time_lineno[0] + 1, "import traceback\n")

        fixture_path_lineno = [
            i for i, line in enumerate(data) if "def get_fixture_path" in line
        ]
        assert len(fixture_path_lineno) == 1
        data.insert(
            fixture_path_lineno[0] + 2,
            "    start_path = (current_file := traceback.extract_stack()[idx:=-1].filename)\n",
        )
        data.insert(
            fixture_path_lineno[0] + 3,
            "    while start_path == current_file:\n",
        )
        data.insert(
            fixture_path_lineno[0] + 4,
            "        start_path = traceback.extract_stack()[idx:=idx-1].filename\n",
        )
        data[fixture_path_lineno[0] + 9] = data[fixture_path_lineno[0] + 9].replace(
            "__file__", "start_path"
        )
        data[fixture_path_lineno[0] + 11] = data[fixture_path_lineno[0] + 11].replace(
            "__file__", "start_path"
        )

        with open(os.path.join(PACKAGE_DIR, "common.py"), "w") as new_file:
            new_file.writelines(data)

        # modify diagnostics file
        with open(os.path.join(PACKAGE_DIR, "components", "diagnostics", "__init__.py"), "r") as original_file:
            data = original_file.readlines()

        diagnostics_lineno = [
            i for i, line in enumerate(data) if "from tests.typing" in line
        ]
        assert len(diagnostics_lineno) == 1
        data[diagnostics_lineno[0]] = data[diagnostics_lineno[0]].replace(
            "tests.typing","pytest_homeassistant_custom_component.typing"
        )

        with open(os.path.join(PACKAGE_DIR, "components", "diagnostics", "__init__.py"), "w") as new_file:
            new_file.writelines(data)


    if ha_version != current_version or regen:
        process_files()
        with open(HA_VERSION_FILE, "w") as f:
            f.write(ha_version)
    else:
        print("Already up to date")

if __name__=="__main__":
    cli()
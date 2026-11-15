# Instructions for Running

## Quick start

Run the script:

```bash
./run_report.sh
```

The script does four steps:

1. It finds the virtual environment in `.venv`.
2. It creates `.venv` with Python 3.11 when the folder is missing.
3. It installs `requirements.txt` when the file changed.
4. It writes the report to the `output` folder. The file name has the date and
   the time.

The script uses `.venv`. To use a different folder, set `VENV_DIR`:

```bash
VENV_DIR=my_env ./run_report.sh
```

After the environment exists, you can also run the report directly:

```bash
.venv/bin/python tanita_report.py DATA1.CSV
```

## Manual environment setup

The versions in `requirements.txt` need Python 3.11. The system Python is 3.14.
The install fails on Python 3.14, because 11 packages have no wheel for it.
Use the uv-managed Python 3.11:

```bash
uv venv --python 3.11 --seed .venv
.venv/bin/pip install -r requirements.txt
```

Do not use `python3 -m venv`. That command uses the system Python 3.14.

## Report options

Put the Tanita export in the project directory. Then run:

```bash
.venv/bin/python tanita_report.py DATA1.CSV
```

The command writes a PDF. The file name has the date and the time of the run,
for example `tanita_report_2026-11-15_10-26-42.pdf`. The report has four pages:

1. The three most recent measurements.
2. A body diagram with fat and muscle for each segment.
3. Charts for body mass, BMI and fat.
4. Charts for muscle and the health markers.

Options:

```bash
.venv/bin/python tanita_report.py DATA1.CSV -o report.pdf
.venv/bin/python tanita_report.py DATA1.CSV --html report.html
.venv/bin/python tanita_report.py DATA1.CSV --raw
.venv/bin/python tanita_report.py DATA1.CSV --lang en
```

- `-o` sets the output file. If you omit `-o`, the name has the date and the
  time of the run. A `.html` suffix writes HTML.
- `--html` also writes a self-contained HTML file.
- `--raw` keeps all rows, including two rows from the same day. The default
  keeps the last measurement of each day.
- `--lang en` writes the report in English.

## Use the notebook (optional)

The notebook is the old report path. It still works.

```bash
.venv/bin/jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser
```

Then open `tanita_report.ipynb`.

The information is based on [this repository](https://github.com/cab938/tanita).

---

# License

This project is released into the public domain under the Unlicense.

To the extent possible under law, the author(s) have dedicated all copyright and related rights to this software to the public domain worldwide. This software is distributed without any warranty.

You should have received a copy of the Unlicense along with this software. If not, see [unlicense.org](http://unlicense.org/).

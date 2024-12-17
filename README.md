# honeybee-openstudio

Honeybee extension for translation to/from OpenStudio.

Specifically, this package extends [honeybee-core](https://github.com/ladybug-tools/honeybee-core) and [honeybee-energy](https://github.com/ladybug-tools/honeybee-energy) to perform translations to/from OpenStudio using the [OpenStudio](https://github.com/NREL/OpenStudio) SDK.

## Installation

`pip install -U honeybe-openstudio`

## QuickStart

```console
import honeybee_openstudio
```

## [API Documentation](http://ladybug-tools.github.io/honeybee-openstudio/docs)

## Local Development

1. Clone this repo locally
```console
git clone git@github.com:ladybug-tools/honeybee-openstudio

# or

git clone https://github.com/ladybug-tools/honeybee-openstudio
```
2. Install dependencies:
```
cd honeybee-openstudio
pip install -r dev-requirements.txt
pip install -r requirements.txt
```

3. Run Tests:
```console
python -m pytest tests/
```

4. Generate Documentation:
```console
sphinx-apidoc -f -e -d 4 -o ./docs ./honeybee_openstudio
sphinx-build -b html ./docs ./docs/_build/docs
```
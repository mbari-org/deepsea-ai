# Deploy to PyPi test

```shell
poetry publish --username <user> --password <password> -r testpypi --dry-run
```

# Run commands in poetry shell

```shell
poetry install
poetry shell
poetry run python deepsea_ai process --input-s3 s3://test-dcline-in --output-s3 s3://test-dcline-out
```
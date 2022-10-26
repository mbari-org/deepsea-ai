# DeepSeaAI Changelog

## [1.6.2](https://github.com/mbari-org/deepsea-ai/compare/v1.6.1...v1.6.2) (2022-10-26)


### Performance Improvements

* bump default role session duration to 12 hours ([c930672](https://github.com/mbari-org/deepsea-ai/commit/c930672794b5ce6409dced6b303fb13aaf282b22))

## [1.6.1](https://github.com/mbari-org/deepsea-ai/compare/v1.6.0...v1.6.1) (2022-10-26)


### Bug Fixes

* correct logic for bucket check ([451a153](https://github.com/mbari-org/deepsea-ai/commit/451a153cfd377b8ae06f76b1c5d18aa1f70ee5c2))


### Performance Improvements

* bump default role session duration ([fae4a4a](https://github.com/mbari-org/deepsea-ai/commit/fae4a4ab7277d12b453a22ec2114dd4cdb789ce3))

# [1.6.0](https://github.com/mbari-org/deepsea-ai/compare/v1.5.1...v1.6.0) (2022-10-24)


### Features

* exit training on bucket failure ([28dd6a0](https://github.com/mbari-org/deepsea-ai/commit/28dd6a0d1fa9d119650d3c9f9118a90458649747))

## [1.5.1](https://github.com/mbari-org/deepsea-ai/compare/v1.5.0...v1.5.1) (2022-10-24)


### Bug Fixes

* correct policy arn, print SageMaker role for clarity and quiet down the config parse print ([542af3a](https://github.com/mbari-org/deepsea-ai/commit/542af3af87e238fe811ed5dba916b052fa8acf69))

# [1.5.0](https://github.com/mbari-org/deepsea-ai/compare/v1.4.0...v1.5.0) (2022-10-17)


### Bug Fixes

* correct uri for training/processing ([2b13fa6](https://github.com/mbari-org/deepsea-ai/commit/2b13fa6b3bfbed9b70c69787e1225ca3c1f1d4db))
* downgrade unlink for python3.7 support ([fbba59e](https://github.com/mbari-org/deepsea-ai/commit/fbba59ed338c4b270f5e3c4dbbde9accd03ddba2))
* non static method and return missing arn ([8dd846d](https://github.com/mbari-org/deepsea-ai/commit/8dd846d117db5847f589212a6893d770f1de04d2))


### Features

* added AWS setup command ([2d6b793](https://github.com/mbari-org/deepsea-ai/commit/2d6b7934ec68827bf8b772f91128b66acdb47a2b))

# [1.4.0](https://github.com/mbari-org/deepsea-ai/compare/v1.3.3...v1.4.0) (2022-09-27)


### Features

* switched to the latest public ecr images as default ([ac332e1](https://github.com/mbari-org/deepsea-ai/commit/ac332e1e398883930dd9f954ca76e341ceb2bfe9))

## [1.3.3](https://github.com/mbari-org/deepsea-ai/compare/v1.3.2...v1.3.3) (2022-09-26)


### Bug Fixes

* remove , from tags - these throw InvalidTag exceptions in boto3 and fix video and job in ecs args ([20a859f](https://github.com/mbari-org/deepsea-ai/commit/20a859fde57cc86d67828f71f3c4db9c2d288b05))

## [1.3.2](https://github.com/mbari-org/deepsea-ai/compare/v1.3.1...v1.3.2) (2022-09-26)


### Bug Fixes

* typo fix ([9ed0a2a](https://github.com/mbari-org/deepsea-ai/commit/9ed0a2a4b840ad6b1b59356cf38719cbd4ea1a9c))

## [1.3.1](https://github.com/mbari-org/deepsea-ai/compare/v1.3.0...v1.3.1) (2022-09-26)


### Bug Fixes

* remove any leading / for video upload ([aa419f7](https://github.com/mbari-org/deepsea-ai/commit/aa419f75584e17d630a0c4cf4fb0de8c41a44a83))

# [1.3.0](https://github.com/mbari-org/deepsea-ai/compare/v1.2.0...v1.3.0) (2022-09-26)


### Bug Fixes

* correct instance type var which broke after refactor ([9631304](https://github.com/mbari-org/deepsea-ai/commit/9631304aeb2c1f80d69c597b48e68a9e990f05a6))
* put back in check_videos which was accidentally removed ([36829dc](https://github.com/mbari-org/deepsea-ai/commit/36829dc66647cee0b959b539ccd49d81f12b7d8d))


### Features

* added config.ini support to support modifying tags, docker uris, and allocate process disk based on video size and command ([701623e](https://github.com/mbari-org/deepsea-ai/commit/701623e11ceff4fe60ae82c50717401b3b92dfa4))

# [1.2.0](https://github.com/mbari-org/deepsea-ai/compare/v1.1.1...v1.2.0) (2022-09-19)


### Features

* bumped training docker image to deepsea-yolov5:1.0.1 ([f0c499c](https://github.com/mbari-org/deepsea-ai/commit/f0c499cf26b72dc2b3405c7afa0c0fb3a59a2c52))

## [1.1.1](https://github.com/mbari-org/deepsea-ai/compare/v1.1.0...v1.1.1) (2022-09-18)


### Bug Fixes

* correction in training volume size estimate and some minor documentation fixes ([0593eef](https://github.com/mbari-org/deepsea-ai/commit/0593eef4f45e2495813f8bb74db1ed74671a8e73))

# [1.1.0](https://github.com/mbari-org/deepsea-ai/compare/v1.0.1...v1.1.0) (2022-09-13)


### Features

* added test of expected path for split command ([19c5291](https://github.com/mbari-org/deepsea-ai/commit/19c5291c2fca9ca2b7ff16e52e6a23a2a947b1d7))

## [1.0.1](https://github.com/mbari-org/deepsea-ai/compare/v1.0.0...v1.0.1) (2022-09-10)


### Performance Improvements

* bumped the boto3 and added awscli to default install to simplify use ([40e946a](https://github.com/mbari-org/deepsea-ai/commit/40e946ad3af1156a3892210bde7ab98fa0b38d1f))

# DeepSea AI PyPi Changelog

# 1.0.0 (2022-09-02)

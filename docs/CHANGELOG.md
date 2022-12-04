# DeepSeaAI Changelog

# [1.16.0](https://github.com/mbari-org/deepsea-ai/compare/v1.15.0...v1.16.0) (2022-12-04)


### Features

* add suppport for Users/ and home/ prefixes ([e605e4c](https://github.com/mbari-org/deepsea-ai/commit/e605e4c81107d10de6c338a8e814cd43df73b6dc))

# [1.15.0](https://github.com/mbari-org/deepsea-ai/compare/v1.14.1...v1.15.0) (2022-11-20)


### Features

* added support for passing in custom trained ReID weights for testing and add yolo.txt file back into tar.gz ([a2728f8](https://github.com/mbari-org/deepsea-ai/commit/a2728f87a9d00f5045b117327adfcb14e9e44af7))

## [1.14.1](https://github.com/mbari-org/deepsea-ai/compare/v1.14.0...v1.14.1) (2022-11-18)


### Performance Improvements

* get rid of empty / prefixes in s3 calls and add iou pass through to process ([0c381a0](https://github.com/mbari-org/deepsea-ai/commit/0c381a0155fe62da323470c9083f0ea85d0a0c99))

# [1.14.0](https://github.com/mbari-org/deepsea-ai/compare/v1.13.1...v1.14.0) (2022-11-11)


### Features

* bump strong sort docker images ([c98e428](https://github.com/mbari-org/deepsea-ai/commit/c98e42815796a25f1e7d499a791816d04ff73873))

## [1.13.1](https://github.com/mbari-org/deepsea-ai/compare/v1.13.0...v1.13.1) (2022-11-11)


### Bug Fixes

* strip rightmost / which errors process command out the with "bucket does not exist" error ([53fa17e](https://github.com/mbari-org/deepsea-ai/commit/53fa17e04c09362a7e20e9afa73cf0d5c0f11ac3))

# [1.13.0](https://github.com/mbari-org/deepsea-ai/compare/v1.12.0...v1.13.0) (2022-11-11)


### Features

* add instance-type option to process for Duane ([e60b2de](https://github.com/mbari-org/deepsea-ai/commit/e60b2de194bd67215b1eb71f8b4c7fb396fcdb51))

# [1.12.0](https://github.com/mbari-org/deepsea-ai/compare/v1.11.0...v1.12.0) (2022-11-11)


### Features

* pass in iou and conf for batch ([d8b4258](https://github.com/mbari-org/deepsea-ai/commit/d8b4258c5dfe4515ad06a3606bd4e0418ac246b4))

# [1.11.0](https://github.com/mbari-org/deepsea-ai/compare/v1.10.0...v1.11.0) (2022-11-10)


### Features

* consistent prefix naming ([3967013](https://github.com/mbari-org/deepsea-ai/commit/3967013080010808e686c5aed385fde22e76e0aa))

# [1.10.0](https://github.com/mbari-org/deepsea-ai/compare/v1.9.0...v1.10.0) (2022-11-09)


### Features

* added mirror as optional command ([01c7fdf](https://github.com/mbari-org/deepsea-ai/commit/01c7fdf35e1db035f25379e82febe44bf36bafd4))

# [1.9.0](https://github.com/mbari-org/deepsea-ai/compare/v1.8.3...v1.9.0) (2022-11-09)


### Features

* better formatting of scaling output and force cluster name as default ([adace33](https://github.com/mbari-org/deepsea-ai/commit/adace3389c51c9e0d54bfa74ea2ad99f62e0062a))

## [1.8.3](https://github.com/mbari-org/deepsea-ai/compare/v1.8.2...v1.8.3) (2022-11-09)


### Bug Fixes

* improved parsing to fetch the username in both subaccounts and a root leve account by the Arn ([a1b4b6d](https://github.com/mbari-org/deepsea-ai/commit/a1b4b6dcf41f2bacbd1e5b06e1230c1ace5fa911))

## [1.8.2](https://github.com/mbari-org/deepsea-ai/compare/v1.8.1...v1.8.2) (2022-11-08)


### Performance Improvements

* require cluster and job description for batch process ([22591b3](https://github.com/mbari-org/deepsea-ai/commit/22591b3b07f7dfa08dd2d59eefdc6720b81a473c))

## [1.8.1](https://github.com/mbari-org/deepsea-ai/compare/v1.8.0...v1.8.1) (2022-11-08)


### Bug Fixes

* add GetAndPassRolePolicy to allow getting and passing of roles and scope boto3 to the profile set by AWS_PROFILE ([425b3ce](https://github.com/mbari-org/deepsea-ai/commit/425b3ce360548062cacefd53968ab90c25733958))
* correct fetching of username ([346cfdd](https://github.com/mbari-org/deepsea-ai/commit/346cfdd0fb3e300b1a2eae57a11f617a2d6f24e5))
* exit on error if any missing data during upload ([ff966d6](https://github.com/mbari-org/deepsea-ai/commit/ff966d6c276413207bc48c501ffb2c7ee0552ab6))

# [1.8.0](https://github.com/mbari-org/deepsea-ai/compare/v1.7.1...v1.8.0) (2022-11-02)


### Bug Fixes

* correct path for default .ini store ([23c1b0f](https://github.com/mbari-org/deepsea-ai/commit/23c1b0f7417e1b318a932e3c507abfe2f5261c2c))


### Features

* make track queue strong and deep sort docker images the default ([ce47580](https://github.com/mbari-org/deepsea-ai/commit/ce47580e0c65cd290bcdaae80317c755295fcec8))

## [1.7.1](https://github.com/mbari-org/deepsea-ai/compare/v1.7.0...v1.7.1) (2022-10-31)


### Bug Fixes

* added -j option back in and handle small < 1 GB videos ([fb192fa](https://github.com/mbari-org/deepsea-ai/commit/fb192fac2e4856d999a27fe3a05f607e18b4d342))

# [1.7.0](https://github.com/mbari-org/deepsea-ai/compare/v1.6.3...v1.7.0) (2022-10-28)


### Features

* beginnings of monitoring of ECS; added ASG pring ([02c6328](https://github.com/mbari-org/deepsea-ai/commit/02c63288707140fddcf124c06beb301be3baca9f))

## [1.6.3](https://github.com/mbari-org/deepsea-ai/compare/v1.6.2...v1.6.3) (2022-10-27)


### Bug Fixes

* correct args for video upload in batch ([349e79f](https://github.com/mbari-org/deepsea-ai/commit/349e79f5d64eb6929878e5dace2199c6530a6b16))

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

#!/usr/bin/env node
import 'source-map-support/register'
import * as cdk from 'aws-cdk-lib'
import * as fs from 'fs'
import 'process'
import { load } from 'js-yaml'
import { readFile } from 'fs/promises'
import { AutoScalingTaskStack } from '../lib/ecs_task_autoscaling'
import { TaskConfig } from '../lib/config'

async function main() {

    // Read in the cfg yaml file as defined in the CDK_STACK_CONFIG environment variable
    if (!process.env.CDK_STACK_CONFIG) {
        console.error('CDK_STACK_CONFIG environment variable not found.')
        process.exit(1)
    }
    const cfg = load(await readFile(process.env.CDK_STACK_CONFIG, "utf8")) as TaskConfig
    console.log(cfg)

    const app = new cdk.App()

    const id = cfg.StackName
    const description = `${cfg.StackName} elastic cluster for processing underwater video`
    const tags = { // MBARI tags projects to track costs - replace with your company tags
      'mbari:project-number': process.env.CDK_DEFAULT_PROJECT_NUMBER || "000000",
      'mbari:description': description,
      'mbari:stage': 'prod',
    }

    new AutoScalingTaskStack(app, cfg, id,{
      env: {
        account: process.env.CDK_DEPLOY_ACCOUNT || process.env.CDK_DEFAULT_ACCOUNT ,
        region:  process.env.CDK_DEPLOY_REGION || process.env.CDK_DEFAULT_REGION
      },
      tags: tags,
      // Add a meaningful description to store with in CloudFormation service console
      description: description
    })

    console.log('Cluster created with tags :')
    for (const [key, value] of Object.entries(tags)) {
      console.log(key, value)
    }
    console.log('Use these for cost accounting')
    app.synth()
}

main().catch((e) => {
    console.error(e)
    process.exit(1)
})

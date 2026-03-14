terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ── Placeholder for ECS / Fargate deployment ──
# resource "aws_ecs_cluster" "main" {
#   name = "healthpredict-cluster"
# }

# resource "aws_ecs_service" "app_service" {
#   name            = "healthpredict-service"
#   cluster         = aws_ecs_cluster.main.id
#   task_definition = aws_ecs_task_definition.app.arn
#   desired_count   = 2
#   launch_type     = "FARGATE"
# }

# resource "aws_ecs_task_definition" "app" {
#   family                   = "healthpredict-task"
#   network_mode             = "awsvpc"
#   requires_compatibilities = ["FARGATE"]
#   cpu                      = "256"
#   memory                   = "512"
#   container_definitions = jsonencode([{
#     name  = "healthpredict-container"
#     image = "healthpredict/app:latest"
#     portMappings = [{
#       containerPort = 8000
#       hostPort      = 8000
#     }]
#   }])
# }

variable "aws_region" {
  description = "The AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g. dev, prod)"
  type        = string
  default     = "prod"
}

variable "db_password" {
  description = "Master password for the PostgreSQL RDS instance"
  type        = string
  sensitive   = true
}

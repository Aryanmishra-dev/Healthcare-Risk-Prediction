output "eks_cluster_endpoint" {
  description = "Endpoint for your Kubernetes API server"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "rds_endpoint" {
  description = "Connection endpoint for the RDS PostgreSQL database"
  value       = aws_db_instance.audit_db.endpoint
}

output "s3_model_bucket_name" {
  description = "Name of the S3 bucket holding ML models"
  value       = aws_s3_bucket.model_artifacts.id
}

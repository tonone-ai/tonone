# FIXTURE FILE — intentionally expensive Terraform for Forge cost tests.
# DO NOT deploy this configuration.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# Expensive on-demand instance — should trigger HIGH/CRITICAL cost finding
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "m5.4xlarge"

  tags = {
    Name = "web-server"
  }
}

# RDS without reserved pricing — HIGH cost finding
resource "aws_db_instance" "main" {
  identifier        = "main-db"
  engine            = "postgres"
  engine_version    = "15.4"
  instance_class    = "db.r6g.xlarge"
  allocated_storage = 100
  username          = "admin"
  password          = "placeholder"
  skip_final_snapshot = true
}

# NAT gateway — steady per-hour cost
resource "aws_nat_gateway" "main" {
  allocation_id = "eipalloc-placeholder"
  subnet_id     = "subnet-placeholder"
}

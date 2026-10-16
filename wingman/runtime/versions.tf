terraform {
  required_version = ">= 1.11.0"
  required_providers {
    xcsh = {
      source  = "f5-sales-demo/xcsh"
      version = "= 15.10.2"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "= 3.3.0"
    }
  }
}
provider "xcsh" {}
provider "kubernetes" {
  config_path    = var.kubeconfig_file
  config_context = var.kubeconfig_context
}

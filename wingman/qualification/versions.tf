terraform {
  required_version = null
  required_providers {
    external = {
      source  = "hashicorp/external"
      version = ">= 0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 0"
    }
  }
}
provider "kubernetes" {
  config_path    = var.kubeconfig_file
  config_context = var.kubeconfig_context
}

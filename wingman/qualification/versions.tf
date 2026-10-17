terraform {
  required_providers {
    kubernetes = {
      source = "hashicorp/kubernetes"
    }
  }
}
provider "kubernetes" {
  config_path    = var.kubeconfig_file
  config_context = var.kubeconfig_context
}

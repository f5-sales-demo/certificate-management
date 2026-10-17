terraform {
  required_providers {
    xcsh = {
      source = "f5-sales-demo/xcsh"
    }
    kubernetes = {
      source = "hashicorp/kubernetes"
    }
  }
}
provider "xcsh" {}
provider "kubernetes" {
  config_path    = var.kubeconfig_file
  config_context = var.kubeconfig_context
}

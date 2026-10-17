terraform {
  required_version = null
  required_providers {
    xcsh = {
      source  = "f5-sales-demo/xcsh"
      version = ">= 0"
    }
  }
}

# XCSH_API_URL and XCSH_API_TOKEN configure the provider, without a CLI.
provider "xcsh" {}

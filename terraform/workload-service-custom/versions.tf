terraform {
  required_version = ">= 1.11.0"
  required_providers {
    xcsh = {
      source = "f5-sales-demo/xcsh"
    }
  }
}

# XCSH_API_URL and XCSH_API_TOKEN configure the provider, without a CLI.
provider "xcsh" {}

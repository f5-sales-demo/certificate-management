terraform {
  required_version = ">= 1.11.0"
  required_providers {
    xcsh = {
      source  = "f5-sales-demo/xcsh"
      version = "= 15.10.2"
    }
  }
}
provider "xcsh" {}

terraform {
  required_version = ">= 1.11.0"
  required_providers {
    xcsh = {
      source  = "f5-sales-demo/xcsh"
      version = "= 15.8.3"
    }
  }
}
# The Secret Policy candidate must be released and this pin advanced before delivery.
# Local verification uses an explicit dev_override; it is not published acceptance.
provider "xcsh" {}

# cdn origin mtls

Copy this directory’s `.tf` files into a dedicated private working directory and state.
Use Terraform 1.11+ and provider 15.7.2. Authenticate through `XCSH_API_URL` and
`XCSH_API_TOKEN`; no xcsh or vesctl installation is required.

Supply the existing namespace and unique owner name plus the explicit prerequisite
variables in `variables.tf`. Keep private input files, variable files, plans, logs,
and state outside Git. Review a saved plan before applying.

See the [walkthrough](https://f5-sales-demo.github.io/certificate-management/en/terraform/)
and [surface prerequisites](https://f5-sales-demo.github.io/certificate-management/en/terraform/certificate-surfaces/).
Choose cleanup by reviewing `terraform plan -destroy`; the namespace is a data source.

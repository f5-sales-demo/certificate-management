# workload service custom

Copy this directory’s `.tf` files into a dedicated private working directory and state.
Use current published Terraform and `f5-sales-demo/xcsh` provider artifacts.
Run `terraform init -upgrade` before creating a new plan. Authenticate through `XCSH_API_URL` and
`XCSH_API_TOKEN`; no xcsh or vesctl installation is required.

Supply the existing namespace and unique owner name plus the explicit prerequisite
variables in `variables.tf`. Keep private input files, variable files, plans, logs,
and state outside Git. Review a saved plan before applying.

See the [walkthrough](https://f5-sales-demo.github.io/certificate-management/en/terraform/)
and [surface prerequisites](https://f5-sales-demo.github.io/certificate-management/en/terraform/certificate-surfaces/).
Choose cleanup by reviewing `terraform plan -destroy`; the namespace is a data source.

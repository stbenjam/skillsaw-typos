# Project Standards

This repository contains our analytics service. Follow these instructions when
making changes to the codebase.

## Build and Test

- Build the project with `make build` to compile all source files.
- Run the test suite with `make test` before submitting changes.
- Keep the test files and source code in seperate directories.

## Code Conventions

- All handlers should recieve validated input from the middleware layer.
- Database queries must be parameterized to prevent SQL injection.
- Use the `logger` package for all output — never print to stdout directly.

## Deployment

```bash
# This typo inside a code block should NOT be flagged
echo "Deploying to teh server"
./deploy.sh --target staging
```

- Deployments are managed through our CI/CD pipeline.
- A deployment failure occured last quarter due to missing environment variables.
- Document any configuration changes in the `docs/` directory.

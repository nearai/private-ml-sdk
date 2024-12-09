# Yocto support for DStack Guest

This project implements Yocto layer and the overall build scripts for DStack Base OS image.

## Build

See https://github.com/Dstack-TEE/dstack for more details.

## Reproducible Build The Guest Image

### Pre-requisites

- X86_64 Linux system with Docker installed

### Build commands

```bash
git clone https://github.com/Dstack-TEE/meta-dstack.git
cd meta-dstack/repro-build/
./repro-build.sh
```

## License

This project is licensed under the MIT License. See the LICENSE file for more details.

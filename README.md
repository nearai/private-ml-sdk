# Yocto support for DStack Guest

This project implements Yocto layer and the overall build scripts for DStack Base OS image.

## Build

```bash
git clone https://github.com/Dstack-TEE/meta-dstack.git --recursive
cd meta-dstack
source dev-setup

mkdir dstack/build
cd dstack/build

../build.sh
# Edit the config, and build again
../build.sh
```

## License

This project is licensed under the MIT License. See the LICENSE file for more details.

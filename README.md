    # SigmaOS-simple-scan

    Scanner (SANE) frontend

    Part of the **SigmaOS** sovereign operating-system ecosystem — a multi-repository
    distribution modelled on Linux Mint and Omarchy Linux. See the parent
    [`SigmaOS`](https://github.com/AaryanSinghChauhan09/SigmaOS) repository for the
    full component index.

    ## Upstream inspirations
    - https://github.com/linuxmint/simple-scan

    ## Design principles applied
    - **Separation of Concerns**
- **Defensive Programming**
- **Fail-Fast**
- **KISS**
- **Deterministic Testing**

    ## Usage
    Verbs: `devices, scan-plan, page, output`

    ```
    $ sigma-scan devices scanimage-L.txt
genesys:libusb:001:004  Genesys USB flatbed scanner
$ sigma-scan scan-plan --device 'genesys:libusb:001:004' --dpi 300
scanimage --device genesys:libusb:001:004 --resolution 300 --mode color --format=png
$ sigma-scan page --count 3
--batch --batch-count 3 --batch-start 1
$ sigma-scan output --pattern 'page-%d.png' --count 3
page-1.png page-2.png page-3.png

    ```

    ## Build & test
    ```
    make build
    make test
    ```

    ## Licence
    GNU General Public License v3.0 (FOSS).

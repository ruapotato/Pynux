// tests/u-binary/src/cpp_demo/hello.cc -- U24 fixture: first C++
// static-PIE binary to run on Hamnix.
//
// U22 proved a C static-PIE glibc binary (heap + FILE* I/O + printf
// variety + time) works. U24 widens the surface to libstdc++:
//
//   * iostreams (std::cout)         -- TLS-backed locale state,
//                                      static-init __ioinit ctor,
//                                      writev to stdout via glibc.
//   * std::vector + std::sort       -- libstdc++ allocator path
//                                      (operator new -> malloc -> brk).
//   * std::string concatenation     -- short-string optimisation path
//                                      + heap when result is long.
//   * try/throw/catch               -- libgcc _Unwind_RaiseException,
//                                      .eh_frame walk via
//                                      _dl_iterate_phdr, which keys off
//                                      auxv AT_PHDR/AT_PHENT/AT_PHNUM.
//
// Markers on serial (asserted by scripts/test_u24_cpp_demo.sh):
//   "U24: cpp hello via std::cout"
//   "U24: sorted=1 2 3 5 8 9 "
//   "U24: hello, world!"
//   "U24: exception caught"
//
// Build: g++ -static-pie -O2. Same OSABI=Linux stamp as the U22 C
// fixture so the U1 detect path is unambiguous.

#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <stdexcept>

int main() {
    std::cout << "U24: cpp hello via std::cout\n";

    std::vector<int> v = {5, 2, 8, 1, 9, 3};
    std::sort(v.begin(), v.end());
    std::cout << "U24: sorted=";
    for (int x : v) std::cout << x << " ";
    std::cout << "\n";

    std::string s = "world";
    s = std::string("hello, ") + s + "!";
    std::cout << "U24: " << s << "\n";

    try {
        throw std::runtime_error("U24: exception caught");
    } catch (const std::exception &e) {
        std::cout << e.what() << "\n";
    }

    return 0;
}

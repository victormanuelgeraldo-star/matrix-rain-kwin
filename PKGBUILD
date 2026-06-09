# Maintainer: victormanuelgeraldo-star
pkgname=matrix-rain-kwin
pkgver=1.0.0
pkgrel=1
pkgdesc="Green Matrix glyph-rain overlay when apps open/close on KDE Plasma (KWin Wayland)"
arch=('any')
url="https://github.com/victormanuelgeraldo-star/matrix-rain-kwin"
license=('GPL-3.0-or-later')
depends=('python' 'python-gobject' 'gtk3' 'gtk-layer-shell' 'noto-fonts-cjk')
optdepends=('kwin: required at runtime (KDE Plasma 6, Wayland)')
source=("$pkgname-$pkgver.tar.gz::$url/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('SKIP')
install="$pkgname.install"

package() {
    cd "$pkgname-$pkgver"

    # overlay daemon
    install -Dm644 src/matrixrain-daemon.py \
        "$pkgdir/usr/lib/$pkgname/matrixrain-daemon.py"

    # systemd user service (points at the /usr/lib daemon)
    install -Dm644 packaging/matrixrain.service \
        "$pkgdir/usr/lib/systemd/user/matrixrain.service"

    # KWin trigger script
    install -Dm644 kwin-script/matrixraintrigger/metadata.json \
        "$pkgdir/usr/share/kwin/scripts/matrixraintrigger/metadata.json"
    install -Dm644 kwin-script/matrixraintrigger/contents/code/main.js \
        "$pkgdir/usr/share/kwin/scripts/matrixraintrigger/contents/code/main.js"

    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
    install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
}

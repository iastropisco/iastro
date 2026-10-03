"""Renderiza os medalhões zodiacais a partir do SVG, em alta resolução.

Os PNGs em `arquetipos/medalhoes/*.png` têm 512px e o medalhão é usado a
~96px com upscale — o Astro Pisco já ouvia a ser serrilhado. Os arquivos
.svg ao lado são o mesmo desenho em vetor: renderizando na hora na resolução
exata que cada uso pede, a borda sai limpa em qualquer tamanho.

Sem dependência nova: usa o `rsvg-convert` do sistema (librsvg), que já
estava instalado, e cai para o PNG em disco se ele faltar.
"""
import hashlib
import os
import subprocess
import tempfile

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      ".cache-medalhoes")
ESCALA = 4          # desenha 4x maior e reduz: supersampling antialias


def _rsvg(svg, w):
    """Renderiza o SVG com a largura w px, altura conforme o viewBox.

    Sai por arquivo temporário: nesta build do rsvg-convert, `-o -` devolve
    stdout vazio e código 0, ou seja, a renderização em memória não funciona.
    """
    if not os.path.exists(svg):
        return None
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        p = subprocess.run(
            ["rsvg-convert", "-w", str(int(w)), "-o", tmp, svg],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        if p.returncode == 0 and os.path.getsize(tmp) > 0:
            with open(tmp, "rb") as f:
                return f.read()
    except Exception:
        return None
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass
    return None


def render(svg, png, largura):
    """Bytes PNG RGBA do medalhão na largura pedida: do SVG quando há
    (nitidez em qualquer tamanho), do PNG em disco como reserva.

    Só a largura é passada ao rsvg: forçar a altura deformava o símbolo
    (o viewBox do Aries é 309x258, não quadrado).
    """
    os.makedirs(CACHE, exist_ok=True)
    chave = hashlib.sha1(
        ("%s|%d|%s" % (os.path.basename(svg), largura,
                       ESCALA)).encode()).hexdigest()[:20]
    out = os.path.join(CACHE, chave + ".png")
    if os.path.exists(out):
        with open(out, "rb") as f:
            return f.read()
    dados = _rsvg(svg, largura * ESCALA)
    if dados is None:
        if not os.path.exists(png):
            return None
        with open(png, "rb") as f:
            return f.read()
    with open(out, "wb") as f:
        f.write(dados)
    return dados


if __name__ == "__main__":
    import sys
    from PIL import Image
    import io
    d = sys.argv[1] if len(sys.argv) > 1 else \
        "/home/italivre/iastro-ia/arquetipos/medalhoes"
    for n in sorted(os.listdir(d)):
        if not n.endswith(".svg"):
            continue
        base = n[:-4]
        svg, png = os.path.join(d, n), os.path.join(d, base + ".png")
        b = render(svg, png, 96)
        if b is None:
            print("%-14s sem fonte" % base)
            continue
        im = Image.open(io.BytesIO(b))
        print("%-14s %s  %d bytes" % (base, im.size, len(b)))

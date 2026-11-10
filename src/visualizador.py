"""
TP1 - BCC327 - Visualizador principal das árvores CCO.

Reúne leitura (modelo.py), transformações e câmera (transformacoes.py) numa
janela interativa. Os módulos seguintes (rasterização, recorte...) entram
como modos extras deste mesmo programa.

    python src/visualizador.py data/dados_modelos3D/tree3D_Nterm016.vtk
    python src/visualizador.py data/dados_modelos2D/tree2D_Nterm008.vtk --tema escuro
    python src/visualizador.py arquivo.vtk --info              # só estatísticas

Figuras para o relatório (sem abrir janela):
    --exportar-vistas figs/            4 vistas x 2 projeções (PNG)
    --figura-projecoes figs/proj.png   ortográfica x perspectiva só com as
                                       nossas matrizes (matplotlib)
    (aceitam --trans X Y Z, --rot RX RY RZ, --escala S, --vista NOME)
"""
import argparse
import os
import sys

import numpy as np
import pyvista as pv

import modelo as md
import transformacoes as T

FOVY = 30.0  # abertura vertical da câmera, em graus

TEMAS = {
    "claro": dict(base="#ffffff", topo="#d9e2ec", texto="#2b2f36",
                  controle="#59616f", uniforme="#4a7fb0"),
    "escuro": dict(base="#0e1016", topo="#262c3d", texto="#e6e9ef",
                   controle="#aab2c5", uniforme="#7fb2e5"),
}

NOMES_VISTA = {"frontal": "frontal", "lateral": "lateral", "topo": "de topo",
               "isometrica": "isométrica"}

AJUDA = (
    "COMANDOS\n"
    "1 2 4 5   vista: frontal, lateral, topo, isométrica\n"
    "0         projeção: perspectiva / ortográfica\n"
    "6         primitiva: tubos / linhas\n"
    "7         cor por raio: liga / desliga\n"
    "8         zera translação, rotação e escala\n"
    "9         imprime as matrizes M, V, P no terminal\n"
    "F2        antialiasing (supersampling): liga / desliga\n"
    "F1        mostra / esconde esta ajuda\n"
    "mouse     esq: gira  dir/roda: zoom  meio: move"
)


class Cena:
    """Estado: parâmetros do modelo (M) e da câmera (V, P)."""

    def __init__(self, malha):
        self.centro = np.array(malha.center)
        self.diag = malha.length
        self.dist = 2.8 * self.diag
        plano = abs(malha.bounds[5] - malha.bounds[4]) < 1e-12
        self.vista = "frontal" if plano else "isometrica"
        self.ortografica = False
        self.reset()

    def reset(self):
        self.trans = [0.0, 0.0, 0.0]
        self.rot = [0.0, 0.0, 0.0]
        self.esc = 1.0

    def M(self):
        return T.matriz_modelo(self.trans, self.rot, self.esc, self.centro)

    def camera(self):
        return T.camera_da_vista(self.vista, self.centro, self.dist)

    def V(self):
        return T.olhar_para(*self.camera())

    def P(self, aspecto=1.0, ortografica=None):
        ort = self.ortografica if ortografica is None else ortografica
        near, far = 0.1 * self.dist, 10 * self.dist
        if ort:
            # mesma altura visível no plano do alvo que a perspectiva teria
            h = self.dist * np.tan(np.radians(FOVY) / 2)
            return T.ortografica(-h * aspecto, h * aspecto, -h, h, near, far)
        return T.perspectiva(FOVY, aspecto, near, far)


class App:
    def __init__(self, malha, nome_raio, onde, args, nome_arquivo=""):
        self.malha = malha
        self.nome_raio = nome_raio
        self.onde = onde
        self.cmap = args.cmap
        self.tema = TEMAS[args.tema]
        self.nome_arquivo = nome_arquivo
        self.cena = Cena(malha)
        self.stats = md.estatisticas(malha, nome_raio, onde)
        self.clim = [self.stats["r_min"], self.stats["r_max"]]
        self.nome_tubo = nome_raio + ("_pt" if onde == "cell" else "")
        self.modo = args.modo
        self.cor_ligada = True
        self.aa = False
        self.pl = None
        self.ator_linhas = self.ator_tubos = None
        self.txt_ajuda = None
        self.sliders = []

    # ------------------------------------------------------------ construção
    def construir(self, off_screen=False, interface=True):
        t = self.tema
        self.pl = pv.Plotter(off_screen=off_screen, window_size=(1400, 850),
                             title="TP1 BCC327 - Árvores CCO")
        self.pl.set_background(t["base"], top=t["topo"])
        self._criar_atores()
        self.aplicar_modelo()
        self.atualizar_camera()
        self.pl.add_axes(color=t["texto"], line_width=2, viewport=(0.70, 0.02, 0.80, 0.18))
        if interface:
            self._montar_textos()
            self._montar_controles()

    def _criar_atores(self):
        t = self.tema
        barra = dict(title="raio", vertical=True, position_x=0.91, position_y=0.22,
                     width=0.04, height=0.5, n_labels=5, fmt="%.3g",
                     title_font_size=14, label_font_size=12, color=t["texto"])
        self.ator_linhas = self.pl.add_mesh(
            self.malha, scalars=self.nome_raio, cmap=self.cmap, clim=self.clim,
            line_width=3, name="linhas", scalar_bar_args=barra)
        tubos = self.malha.tube(scalars="raio_vis", absolute=True, n_sides=16)
        self.ator_tubos = self.pl.add_mesh(
            tubos, scalars=self.nome_tubo, cmap=self.cmap, clim=self.clim,
            smooth_shading=True, specular=0.3, name="tubos",
            show_scalar_bar=False)
        self._atualizar_visibilidade()

    def _montar_textos(self):
        t = self.tema
        self.pl.add_text(f"Árvore CCO  -  {self.nome_arquivo}", position="upper_edge",
                         font_size=12, color=t["texto"], name="titulo")
        self.txt_ajuda = self.pl.add_text(AJUDA, position="lower_left", font_size=8,
                                          color=t["texto"], font="courier", name="ajuda")
        s = self.stats
        dim = "2D" if s["plano"] else "3D"
        self.pl.add_text(
            f"modelo {dim}\npontos: {s['pontos']}\nsegmentos: {s['segmentos']}\n"
            f"raio mín: {s['r_min']:.3f}\nraio máx: {s['r_max']:.3f}",
            position="lower_right", font_size=9, color=t["texto"], name="stats")

    # ----------------------------------------------------------- atualizações
    def _atualizar_visibilidade(self):
        tubos = self.modo == "tubos"
        self.ator_tubos.SetVisibility(tubos)
        self.ator_linhas.SetVisibility(not tubos)
        for ator in (self.ator_linhas, self.ator_tubos):
            ator.mapper.scalar_visibility = self.cor_ligada
            if not self.cor_ligada:
                ator.prop.color = self.tema["uniforme"]
        try:
            self.pl.scalar_bars["raio"].SetVisibility(self.cor_ligada)
        except Exception:
            pass

    def aplicar_modelo(self):
        """M é calculada por nós (transformacoes.py); o VTK só a multiplica
        pelos vértices na hora de desenhar."""
        M = self.cena.M()
        self.ator_linhas.user_matrix = M
        self.ator_tubos.user_matrix = M
        self.pl.reset_camera_clipping_range()
        self.pl.render()

    def atualizar_camera(self):
        c = self.cena
        eye, alvo, up = c.camera()
        self.pl.camera_position = [tuple(eye), tuple(alvo), tuple(up)]
        self.pl.camera.view_angle = FOVY
        self.pl.camera.parallel_projection = c.ortografica
        if c.ortografica:
            self.pl.camera.parallel_scale = c.dist * np.tan(np.radians(FOVY) / 2)
        self.pl.reset_camera_clipping_range()
        self._hud()
        self.pl.render()

    def _hud(self):
        c = self.cena
        proj = "ortográfica" if c.ortografica else "perspectiva"
        aa = "ligado (SSAA)" if self.aa else "desligado"
        self.pl.add_text(
            f"vista {NOMES_VISTA[c.vista]}  -  projeção {proj}  -  antialiasing {aa}",
            name="hud", position="lower_edge", font_size=10, color=self.tema["texto"])

    # ------------------------------------------------------------------ ações
    def alternar_aa(self):
        self.aa = not self.aa
        if self.aa:
            self.pl.enable_anti_aliasing("ssaa")
        else:
            self.pl.disable_anti_aliasing()
        self._hud()
        self.pl.render()

    def mudar_vista(self, nome):
        self.cena.vista = nome
        self.atualizar_camera()

    def alternar_projecao(self):
        self.cena.ortografica = not self.cena.ortografica
        self.atualizar_camera()

    def alternar_modo(self):
        self.modo = "linhas" if self.modo == "tubos" else "tubos"
        self._atualizar_visibilidade()
        self.pl.render()

    def alternar_cor(self):
        self.cor_ligada = not self.cor_ligada
        self._atualizar_visibilidade()
        self.pl.render()

    def alternar_ajuda(self):
        if self.txt_ajuda is not None:
            self.txt_ajuda.SetVisibility(not self.txt_ajuda.GetVisibility())
            self.pl.render()

    def zerar(self):
        self.cena.reset()
        for sl, inicial in self.sliders:
            sl.GetRepresentation().SetValue(inicial)
        self.aplicar_modelo()

    def imprimir_matrizes(self):
        w, h = self.pl.window_size
        c = self.cena
        with np.printoptions(precision=4, suppress=True):
            print("\nM (modelo: objeto -> mundo)\n", c.M())
            print("V (vista: mundo -> câmera)\n", c.V())
            print(f"P (projeção {'ortográfica' if c.ortografica else 'perspectiva'})\n",
                  c.P(w / h))

    # ------------------------------------------------------------ controles
    def _montar_controles(self):
        c = self.cena
        defs = [
            ("tx (% da diagonal)", (-50, 50), "t", 0),
            ("ty (% da diagonal)", (-50, 50), "t", 1),
            ("tz (% da diagonal)", (-50, 50), "t", 2),
            ("rot x (graus)", (-180, 180), "r", 0),
            ("rot y (graus)", (-180, 180), "r", 1),
            ("rot z (graus)", (-180, 180), "r", 2),
        ]
        y = 0.88

        def fabrica(tipo, i):
            def cb(v):
                if tipo == "t":
                    c.trans[i] = v / 100.0 * c.diag
                else:
                    c.rot[i] = v
                self.aplicar_modelo()
            return cb

        for titulo, faixa, tipo, i in defs:
            self.sliders.append(self._slider(fabrica(tipo, i), faixa, 0.0, titulo, y))
            y -= 0.10

        def cb_esc(v):
            c.esc = v
            self.aplicar_modelo()
        self.sliders.append(self._slider(cb_esc, (0.2, 3.0), 1.0, "escala", y))

        for tecla, nome in (("1", "frontal"), ("2", "lateral"),
                            ("4", "topo"), ("5", "isometrica")):
            self.pl.add_key_event(tecla, lambda n=nome: self.mudar_vista(n))
        self.pl.add_key_event("0", self.alternar_projecao)
        self.pl.add_key_event("6", self.alternar_modo)
        self.pl.add_key_event("7", self.alternar_cor)
        self.pl.add_key_event("8", self.zerar)
        self.pl.add_key_event("9", self.imprimir_matrizes)
        self.pl.add_key_event("F1", self.alternar_ajuda)
        self.pl.add_key_event("F2", self.alternar_aa)

    def _slider(self, cb, faixa, inicial, titulo, y):
        kw = dict(value=inicial, title=titulo, pointa=(0.03, y), pointb=(0.24, y),
                  fmt="%.3g", style="modern", slider_width=0.015, tube_width=0.004,
                  title_height=0.018, color=self.tema["controle"])
        try:
            sl = self.pl.add_slider_widget(cb, list(faixa), interaction_event="always", **kw)
        except TypeError:  # PyVista mais antigo
            sl = self.pl.add_slider_widget(cb, list(faixa), **kw)
        return (sl, inicial)


# ------------------------------------------------------- figuras do relatório
def figura_projecoes(app, saida):
    """Ortográfica x perspectiva usando SÓ as matrizes de transformacoes.py
    (sem passar pelo pipeline do VTK)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection

    c = app.cena
    pts = T.aplicar(c.M(), np.asarray(app.malha.points))
    segs = md.extrair_segmentos(app.malha)
    dados = app.malha.cell_data if app.onde == "cell" else None
    cores = None
    if dados is not None and len(dados[app.nome_raio]) == len(segs):
        cores = np.asarray(dados[app.nome_raio])

    fig, eixos = plt.subplots(1, 2, figsize=(11, 5))
    for ax, ort, nome in ((eixos[0], True, "Projeção ortográfica"),
                          (eixos[1], False, "Projeção perspectiva")):
        ndc = T.projetar(pts, c.V(), c.P(1.0, ortografica=ort))
        lc = LineCollection(ndc[:, :2][segs], cmap=app.cmap, linewidths=1.8)
        if cores is not None:
            lc.set_array(cores)
            lc.set_clim(*app.clim)
        else:
            lc.set_color("k")
        ax.add_collection(lc)
        ax.set_xlim(-1.05, 1.05)
        ax.set_ylim(-1.05, 1.05)
        ax.set_aspect("equal")
        ax.set_title(f"{nome} — vista {c.vista}")
        ax.set_xlabel("x (NDC)")
        ax.set_ylabel("y (NDC)")
    if cores is not None:
        fig.colorbar(lc, ax=eixos, label=f"raio ({app.nome_raio})", shrink=0.8)
    fig.savefig(saida, dpi=150, bbox_inches="tight")
    print(f"Figura salva em {saida}")


def exportar_vistas(app, pasta):
    os.makedirs(pasta, exist_ok=True)
    app.construir(off_screen=True, interface=False)
    c = app.cena
    for nome in T.VISTAS:
        for ort in (False, True):
            c.vista, c.ortografica = nome, ort
            app.atualizar_camera()
            arq = os.path.join(pasta, f"vista_{nome}_{'orto' if ort else 'persp'}.png")
            app.pl.screenshot(arq)
            print("salvo:", arq)


# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arquivo")
    ap.add_argument("--modo", choices=["linhas", "tubos"], default="tubos")
    ap.add_argument("--tema", choices=list(TEMAS), default="claro")
    ap.add_argument("--cmap", default="viridis")
    ap.add_argument("--campo-raio", default=None, help="nome do array de raio, se a detecção falhar")
    ap.add_argument("--escala-raio", type=float, default=None,
                    help="fator do raio nos tubos (só visual). Padrão: automático")
    ap.add_argument("--info", action="store_true", help="só imprime estatísticas")
    ap.add_argument("--vista", choices=list(T.VISTAS), default=None)
    ap.add_argument("--ortografica", action="store_true")
    ap.add_argument("--trans", type=float, nargs=3, default=[0, 0, 0], metavar=("X", "Y", "Z"))
    ap.add_argument("--rot", type=float, nargs=3, default=[0, 0, 0], metavar=("RX", "RY", "RZ"))
    ap.add_argument("--escala", type=float, default=1.0)
    ap.add_argument("--exportar-vistas", default=None, metavar="PASTA")
    ap.add_argument("--figura-projecoes", default=None, metavar="ARQ.png")
    args = ap.parse_args()

    malha = md.carregar_modelo(args.arquivo)
    if args.campo_raio:
        nome_raio = args.campo_raio
        onde = "cell" if nome_raio in malha.cell_data else "point"
    else:
        nome_raio, onde = md.achar_raio(malha)

    md.imprimir_info(malha, nome_raio, onde)
    if args.info or nome_raio is None:
        return

    # o raio pode estar em outra unidade que as coordenadas, então o tubo com
    # o raio "cru" ficaria gigante. Ajuste só visual:
    escala_visual = args.escala_raio
    if escala_visual is None:
        r_max = md.estatisticas(malha, nome_raio, onde)["r_max"]
        escala_visual = 0.03 * malha.length / r_max
    malha = md.preparar_raio(malha, nome_raio, onde, escala_visual)

    app = App(malha, nome_raio, onde, args, nome_arquivo=os.path.basename(args.arquivo))
    c = app.cena
    c.trans, c.rot, c.esc = list(args.trans), list(args.rot), args.escala
    if args.vista:
        c.vista = args.vista
    c.ortografica = args.ortografica

    if args.figura_projecoes:
        figura_projecoes(app, args.figura_projecoes)
    if args.exportar_vistas:
        exportar_vistas(app, args.exportar_vistas)
    if args.figura_projecoes or args.exportar_vistas:
        return

    app.construir()
    app.pl.show()


if __name__ == "__main__":
    sys.exit(main())
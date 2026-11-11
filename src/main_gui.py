"""BCC327 - TP1: interface gráfica única para todo o projeto.

Junta, numa só janela, tudo o que antes era feito por linha de comando:

  * visualizador.py  -> aba "Árvore CCO" (3D interativo, M/V/P, sliders...)
  * didatico.py      -> abas "Bresenham", "Scanline", "Antialiasing", "Recorte",
                       "Recorte de polígonos" (Módulo 7, que fica em recorte.py)

Nenhum módulo do grupo é alterado: a GUI só os importa e os chama. O que
antes ia para o terminal (tabelas, estatísticas) aparece no console embutido.

    python main_gui.py

Coloque este arquivo na mesma pasta de modelo.py, transformacoes.py,
rasterizacao.py, recorte.py, didatico.py e visualizador.py.
"""
import contextlib
import io
import os
import sys
import traceback
from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")  # as figuras do didatico.py são embutidas na janela Qt
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

import numpy as np  # noqa: E402
from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtGui import QFontDatabase  # noqa: E402
from PyQt5.QtWidgets import (  # noqa: E402
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
    QScrollArea, QSlider, QSpinBox, QSplitter, QStackedWidget, QTabWidget,
    QVBoxLayout, QWidget,
)
from pyvistaqt import QtInteractor  # noqa: E402

try:
    from matplotlib.backends.backend_qtagg import (
        FigureCanvasQTAgg, NavigationToolbar2QT)
except ImportError:  # matplotlib mais antigo
    from matplotlib.backends.backend_qt5agg import (
        FigureCanvasQTAgg, NavigationToolbar2QT)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import didatico as D  # noqa: E402
import modelo as md  # noqa: E402
import transformacoes as T  # noqa: E402
import visualizador as vz  # noqa: E402

CMAP = "viridis"
ROTULO_VISTA = {"frontal": "Frontal", "lateral": "Lateral", "topo": "Topo",
                "isometrica": "Isométrica"}


class MainWindow(QMainWindow):
    ABA_CCO = 0

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BCC327 - TP1: Árvores CCO & Computação Gráfica")
        self.resize(1500, 900)

        # estado do modelo carregado
        self.caminho = None
        self.malha = None
        self.nome_raio = self.onde = self.nome_tubo = None
        self.stats = None
        self.escala_auto = 1.0
        self.cena = None
        self.ator_linhas = self.ator_tubos = None
        self.sliders = []
        self._demo = None        # DemoInterativo precisa ficar referenciado
        self._figuras = []

        central = QWidget()
        self.setCentralWidget(central)
        raiz = QHBoxLayout(central)

        # ---------------------------------------------------- painel esquerdo
        esquerda = QWidget()
        esquerda.setMaximumWidth(420)
        col = QVBoxLayout(esquerda)
        barra = QHBoxLayout()
        btn = QPushButton("Abrir VTK...")
        btn.clicked.connect(self.abrir_vtk)
        barra.addWidget(btn)
        self.lbl_arquivo = QLabel("nenhum arquivo")
        self.lbl_arquivo.setWordWrap(True)
        barra.addWidget(self.lbl_arquivo, stretch=1)
        col.addLayout(barra)

        self.tabs = QTabWidget()
        col.addWidget(self.tabs)
        self.tabs.addTab(self._rolavel(self._aba_cco()), "Árvore CCO")
        self.tabs.addTab(self._rolavel(self._aba_bresenham()), "Bresenham")
        self.tabs.addTab(self._rolavel(self._aba_scanline()), "Scanline")
        self.tabs.addTab(self._rolavel(self._aba_antialiasing()), "Antialiasing")
        self.tabs.addTab(self._rolavel(self._aba_recorte()), "Recorte")
        self.tabs.addTab(self._rolavel(self._aba_recorte_poligonos()),
                         "Recorte de polígonos")
        self.tabs.currentChanged.connect(self.ao_mudar_aba)
        raiz.addWidget(esquerda, stretch=0)

        # ----------------------------------------------------- painel direito
        self.plotter = QtInteractor(central)       # único contexto OpenGL
        self.fig_tabs = QTabWidget()               # figuras do matplotlib
        self.stack = QStackedWidget()
        self.stack.addWidget(self.plotter.interactor)
        self.stack.addWidget(self.fig_tabs)

        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.console.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.console.setPlaceholderText(
            "Console: aqui aparecem as tabelas e estatísticas que antes "
            "saíam no terminal.")
        btn_limpar = QPushButton("Limpar console")
        btn_limpar.clicked.connect(self.console.clear)
        rodape = QWidget()
        lr = QVBoxLayout(rodape)
        lr.setContentsMargins(0, 0, 0, 0)
        lr.addWidget(self.console)
        lr.addWidget(btn_limpar)

        divisor = QSplitter(Qt.Vertical)
        divisor.addWidget(self.stack)
        divisor.addWidget(rodape)
        divisor.setStretchFactor(0, 4)
        divisor.setStretchFactor(1, 1)
        raiz.addWidget(divisor, stretch=1)

        self.statusBar().showMessage("Abra um arquivo .vtk para começar.")

    # ======================================================================
    # utilitários de interface
    # ======================================================================
    @staticmethod
    def _rolavel(widget):
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(widget)
        return area

    @staticmethod
    def _grupo(layout_pai, titulo):
        grupo = QGroupBox(titulo)
        lay = QVBoxLayout(grupo)
        layout_pai.addWidget(grupo)
        return lay

    @staticmethod
    def _botao(layout, texto, slot):
        b = QPushButton(texto)
        b.clicked.connect(slot)
        layout.addWidget(b)
        return b

    @staticmethod
    def _combo_vista():
        c = QComboBox()
        c.addItem("Automática", None)
        for nome in T.VISTAS:
            c.addItem(ROTULO_VISTA[nome], nome)
        return c

    @staticmethod
    def _spin(layout, rotulo, minimo, maximo, inicial):
        layout.addWidget(QLabel(rotulo))
        s = QSpinBox()
        s.setRange(minimo, maximo)
        s.setValue(inicial)
        layout.addWidget(s)
        return s

    def _console(self, texto):
        if texto:
            self.console.appendPlainText(texto.rstrip("\n"))
            self.console.verticalScrollBar().setValue(
                self.console.verticalScrollBar().maximum())

    def _erro(self, titulo, exc):
        self.statusBar().showMessage(f"{titulo}: {exc}")
        QMessageBox.warning(self, titulo, str(exc))

    def _exigir_modelo(self):
        if self.caminho is None:
            QMessageBox.information(
                self, "Nenhum modelo", "Abra um arquivo .vtk primeiro "
                "(botão 'Abrir VTK...').")
            return False
        return True

    # ======================================================================
    # carregamento do modelo (equivale ao main() do visualizador.py)
    # ======================================================================
    def abrir_vtk(self):
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Selecionar arquivo VTK", "data/", "VTK (*.vtk)")
        if not caminho:
            return
        try:
            malha = md.carregar_modelo(caminho)
            nome_raio, onde = md.achar_raio(malha)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                md.imprimir_info(malha, nome_raio, onde)
            self._console(f"$ abrir {os.path.basename(caminho)}\n{buf.getvalue()}")
            if nome_raio is None:
                raise ValueError("Não achei o atributo de raio no arquivo "
                                 "(veja os arrays no console).")
            stats = md.estatisticas(malha, nome_raio, onde)
        except Exception as exc:
            self._erro("Erro ao abrir o modelo", exc)
            return

        self.caminho, self.malha = caminho, malha
        self.nome_raio, self.onde, self.stats = nome_raio, onde, stats
        self.nome_tubo = nome_raio + ("_pt" if onde == "cell" else "")
        # o raio pode estar em outra unidade que as coordenadas: ajuste visual
        self.escala_auto = 0.03 * malha.length / stats["r_max"]
        self._preparar_malha()
        self.cena = vz.Cena(malha)

        self.lbl_arquivo.setText(os.path.basename(caminho))
        dim = "2D" if stats["plano"] else "3D"
        self.lbl_stats.setText(
            f"modelo {dim} | pontos: {stats['pontos']} | segmentos: "
            f"{stats['segmentos']}\nraio mín: {stats['r_min']:.4g} | "
            f"raio máx: {stats['r_max']:.4g}")
        self.combo_vista_cco.blockSignals(True)
        self.combo_vista_cco.setCurrentIndex(
            self.combo_vista_cco.findData(self.cena.vista))
        self.combo_vista_cco.blockSignals(False)
        self.chk_orto.blockSignals(True)
        self.chk_orto.setChecked(False)
        self.chk_orto.blockSignals(False)
        self._zerar_sliders()
        self._construir_cena3d()
        self.tabs.setCurrentIndex(self.ABA_CCO)
        self.stack.setCurrentIndex(0)
        self.statusBar().showMessage(f"Modelo carregado: {os.path.basename(caminho)}")

    def _preparar_malha(self):
        md.preparar_raio(self.malha, self.nome_raio, self.onde,
                         self.escala_auto * self.spin_tubo.value())

    # ======================================================================
    # ABA 1: ÁRVORE CCO (3D)
    # ======================================================================
    def _aba_cco(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.lbl_stats = QLabel("Sem modelo.")
        self.lbl_stats.setWordWrap(True)
        lay.addWidget(self.lbl_stats)

        g = self._grupo(lay, "Aparência")
        g.addWidget(QLabel("Primitiva:"))
        self.combo_modo = QComboBox()
        self.combo_modo.addItems(["tubos", "linhas"])
        self.combo_modo.currentIndexChanged.connect(self._atualizar_visibilidade)
        g.addWidget(self.combo_modo)
        self.chk_cor = QCheckBox("Cor por raio")
        self.chk_cor.setChecked(True)
        self.chk_cor.stateChanged.connect(self._atualizar_visibilidade)
        g.addWidget(self.chk_cor)
        g.addWidget(QLabel("Espessura dos tubos (× automático):"))
        self.spin_tubo = QDoubleSpinBox()
        self.spin_tubo.setRange(0.1, 10.0)
        self.spin_tubo.setSingleStep(0.25)
        self.spin_tubo.setValue(1.0)
        self.spin_tubo.editingFinished.connect(self._mudou_espessura)
        g.addWidget(self.spin_tubo)
        g.addWidget(QLabel("Tema:"))
        self.combo_tema = QComboBox()
        self.combo_tema.addItems(list(vz.TEMAS))
        self.combo_tema.currentIndexChanged.connect(self._construir_cena3d)
        g.addWidget(self.combo_tema)

        g = self._grupo(lay, "Câmera (V, P)")
        g.addWidget(QLabel("Vista:"))
        self.combo_vista_cco = QComboBox()
        for nome in T.VISTAS:
            self.combo_vista_cco.addItem(ROTULO_VISTA[nome], nome)
        self.combo_vista_cco.currentIndexChanged.connect(self._mudou_vista)
        g.addWidget(self.combo_vista_cco)
        self.chk_orto = QCheckBox("Projeção ortográfica (senão perspectiva)")
        self.chk_orto.stateChanged.connect(self._mudou_projecao)
        g.addWidget(self.chk_orto)
        self.chk_aa = QCheckBox("Antialiasing do VTK (SSAA)")
        self.chk_aa.stateChanged.connect(self._mudou_aa)
        g.addWidget(self.chk_aa)

        g = self._grupo(lay, "Transformações do modelo (M)")
        self.sliders = []
        defs = [("tx (% da diagonal)", -50, 50, 0, 1.0, "t", 0),
                ("ty (% da diagonal)", -50, 50, 0, 1.0, "t", 1),
                ("tz (% da diagonal)", -50, 50, 0, 1.0, "t", 2),
                ("rot x (graus)", -180, 180, 0, 1.0, "r", 0),
                ("rot y (graus)", -180, 180, 0, 1.0, "r", 1),
                ("rot z (graus)", -180, 180, 0, 1.0, "r", 2),
                ("escala", 20, 300, 100, 0.01, "e", 0)]
        for titulo, mn, mx, ini, fator, tipo, i in defs:
            self._slider(g, titulo, mn, mx, ini, fator, tipo, i)
        self._botao(g, "Zerar transformações", self.zerar)

        g = self._grupo(lay, "Relatório")
        self._botao(g, "Mostrar matrizes M, V, P no console", self.imprimir_matrizes)
        self._botao(g, "Exportar 4 vistas × 2 projeções (PNG)...", self.exportar_vistas)
        self._botao(g, "Figura ortográfica × perspectiva (PNG)...",
                    self.figura_projecoes)
        lay.addStretch()
        return w

    def _slider(self, layout, titulo, mn, mx, ini, fator, tipo, i):
        rot = QLabel()
        sl = QSlider(Qt.Horizontal)
        sl.setRange(mn, mx)
        sl.setValue(ini)

        def atualiza_rotulo(v):
            rot.setText(f"{titulo}: {v * fator:.3g}")

        def mudou(v):
            atualiza_rotulo(v)
            c = self.cena
            if c is None:
                return
            valor = v * fator
            if tipo == "t":
                c.trans[i] = valor / 100.0 * c.diag
            elif tipo == "r":
                c.rot[i] = valor
            else:
                c.esc = valor
            self.aplicar_modelo()

        atualiza_rotulo(ini)
        sl.valueChanged.connect(mudou)
        layout.addWidget(rot)
        layout.addWidget(sl)
        self.sliders.append((sl, ini, atualiza_rotulo))

    def _zerar_sliders(self):
        for sl, ini, atualiza in self.sliders:
            sl.blockSignals(True)
            sl.setValue(ini)
            sl.blockSignals(False)
            atualiza(ini)

    def zerar(self):
        if self.cena is None:
            return
        self.cena.reset()
        self._zerar_sliders()
        self.aplicar_modelo()

    # ---------------------------------------------------------------- cena 3D
    def _construir_cena3d(self, *_):
        """Cria os atores (linhas e tubos) como em App._criar_atores."""
        if self.malha is None:
            return
        t = vz.TEMAS[self.combo_tema.currentText()]
        p = self.plotter
        p.clear()
        p.set_background(t["base"], top=t["topo"])
        barra = dict(title="raio", vertical=True, position_x=0.91,
                     position_y=0.22, width=0.04, height=0.5, n_labels=5,
                     fmt="%.3g", title_font_size=14, label_font_size=12,
                     color=t["texto"])
        clim = [self.stats["r_min"], self.stats["r_max"]]
        self.ator_linhas = p.add_mesh(
            self.malha, scalars=self.nome_raio, cmap=CMAP, clim=clim,
            line_width=3, name="linhas", scalar_bar_args=barra)
        tubos = self.malha.tube(scalars="raio_vis", absolute=True, n_sides=16)
        self.ator_tubos = p.add_mesh(
            tubos, scalars=self.nome_tubo, cmap=CMAP, clim=clim,
            smooth_shading=True, specular=0.3, name="tubos",
            show_scalar_bar=False)
        p.add_axes(color=t["texto"], line_width=2,
                   viewport=(0.70, 0.02, 0.80, 0.18))
        self._atualizar_visibilidade()
        self.aplicar_modelo()
        self.atualizar_camera()

    def _atualizar_visibilidade(self, *_):
        if self.ator_linhas is None:
            return
        tubos = self.combo_modo.currentText() == "tubos"
        cor = self.chk_cor.isChecked()
        self.ator_tubos.SetVisibility(tubos)
        self.ator_linhas.SetVisibility(not tubos)
        uniforme = vz.TEMAS[self.combo_tema.currentText()]["uniforme"]
        for ator in (self.ator_linhas, self.ator_tubos):
            ator.mapper.scalar_visibility = cor
            if not cor:
                ator.prop.color = uniforme
        try:
            self.plotter.scalar_bars["raio"].SetVisibility(cor)
        except Exception:
            pass
        self.plotter.render()

    def aplicar_modelo(self):
        """M vem de transformacoes.py; o VTK só a multiplica pelos vértices."""
        if self.cena is None or self.ator_linhas is None:
            return
        M = self.cena.M()
        self.ator_linhas.user_matrix = M
        self.ator_tubos.user_matrix = M
        self.plotter.reset_camera_clipping_range()
        self.plotter.render()

    def atualizar_camera(self):
        c = self.cena
        if c is None:
            return
        eye, alvo, up = c.camera()
        self.plotter.camera_position = [tuple(eye), tuple(alvo), tuple(up)]
        self.plotter.camera.view_angle = vz.FOVY
        self.plotter.camera.parallel_projection = c.ortografica
        if c.ortografica:
            self.plotter.camera.parallel_scale = c.dist * np.tan(
                np.radians(vz.FOVY) / 2)
        self.plotter.reset_camera_clipping_range()
        self.plotter.render()
        proj = "ortográfica" if c.ortografica else "perspectiva"
        self.statusBar().showMessage(
            f"vista {ROTULO_VISTA[c.vista].lower()} | projeção {proj}")

    def _mudou_vista(self):
        if self.cena is None:
            return
        self.cena.vista = self.combo_vista_cco.currentData()
        self.atualizar_camera()

    def _mudou_projecao(self):
        if self.cena is None:
            return
        self.cena.ortografica = self.chk_orto.isChecked()
        self.atualizar_camera()

    def _mudou_aa(self):
        if self.chk_aa.isChecked():
            self.plotter.enable_anti_aliasing("ssaa")
        else:
            self.plotter.disable_anti_aliasing()
        self.plotter.render()

    def _mudou_espessura(self):
        if self.malha is None:
            return
        self._preparar_malha()
        self._construir_cena3d()

    # ---------------------------------------------------- saídas do relatório
    def imprimir_matrizes(self):
        if self.cena is None:
            return
        c = self.cena
        w = max(self.plotter.interactor.width(), 1)
        h = max(self.plotter.interactor.height(), 1)
        buf = io.StringIO()
        with np.printoptions(precision=4, suppress=True):
            print("M (modelo: objeto -> mundo)\n", c.M(), file=buf)
            print("V (vista: mundo -> câmera)\n", c.V(), file=buf)
            print(f"P (projeção {'ortográfica' if c.ortografica else 'perspectiva'})\n",
                  c.P(w / h), file=buf)
        self._console("$ matrizes\n" + buf.getvalue())

    def exportar_vistas(self):
        """Mesmas 8 imagens do exportar_vistas() do visualizador.py, mas feitas
        no próprio canvas da janela (evita um 2º contexto OpenGL)."""
        if self.cena is None:
            return
        pasta = QFileDialog.getExistingDirectory(self, "Pasta de destino")
        if not pasta:
            return
        c = self.cena
        estado = (c.vista, c.ortografica)
        try:
            for nome in T.VISTAS:
                for ort in (False, True):
                    c.vista, c.ortografica = nome, ort
                    self.atualizar_camera()
                    arq = os.path.join(
                        pasta, f"vista_{nome}_{'orto' if ort else 'persp'}.png")
                    self.plotter.screenshot(arq)
                    self._console(f"salvo: {arq}")
        except Exception as exc:
            self._erro("Erro ao exportar vistas", exc)
        finally:
            c.vista, c.ortografica = estado
            self.atualizar_camera()

    def figura_projecoes(self):
        if self.cena is None:
            return
        arq, _ = QFileDialog.getSaveFileName(
            self, "Salvar figura", "projecoes.png", "PNG (*.png)")
        if not arq:
            return
        proxy = SimpleNamespace(
            cena=self.cena, malha=self.malha, onde=self.onde,
            nome_raio=self.nome_raio, cmap=CMAP,
            clim=[self.stats["r_min"], self.stats["r_max"]])
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                vz.figura_projecoes(proxy, arq)
        except Exception as exc:
            self._erro("Erro ao gerar a figura", exc)
            return
        self._console(buf.getvalue())
        fig = Figure(figsize=(11, 5))
        ax = fig.add_subplot(111)
        ax.imshow(plt.imread(arq))
        ax.axis("off")
        self._mostrar_figuras({"Projeções": fig})

    # ======================================================================
    # ABAS DIDÁTICAS (didatico.py)
    # ======================================================================
    def _aba_bresenham(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        g = self._grupo(lay, "Demonstração")
        self._botao(g, "8 octantes + exemplo numérico", self.bresenham_demo)
        self._botao(g, "Interativo (clique na grade)", self.bresenham_interativo)
        g = self._grupo(lay, "Aplicado à árvore carregada")
        g.addWidget(QLabel("Vista:"))
        self.b_vista = self._combo_vista()
        g.addWidget(self.b_vista)
        self.b_tam = self._spin(g, "Tamanho da imagem (px):", 64, 1600, 600)
        self._botao(g, "Rasterizar árvore (Bresenham x DDA)", self.bresenham_arvore)
        lay.addStretch()
        return w

    def _aba_scanline(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        g = self._grupo(lay, "Demonstração")
        self._botao(g, "Polígono côncavo + tabela por varredura", self.scanline_demo)
        g = self._grupo(lay, "Aplicado à árvore carregada")
        g.addWidget(QLabel("Vista:"))
        self.s_vista = self._combo_vista()
        g.addWidget(self.s_vista)
        self.s_tam = self._spin(g, "Tamanho da imagem (px):", 64, 1600, 600)
        self._botao(g, "Região de interesse sobre a árvore", self.scanline_arvore)
        lay.addStretch()
        return w

    def _aba_antialiasing(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        g = self._grupo(lay, "Parâmetros")
        self.a_k = self._spin(g, "Fator de supersampling k (k×k):", 1, 16, 4)
        self.a_ref = self._spin(g, "Fator da referência:", 2, 32, 8)
        self._botao(g, "Cena de teste (leque de retas)", self.aa_demo)
        g = self._grupo(lay, "Aplicado à árvore carregada")
        g.addWidget(QLabel("Vista:"))
        self.a_vista = self._combo_vista()
        g.addWidget(self.a_vista)
        self.a_tam = self._spin(g, "Tamanho da imagem (px):", 64, 1200, 300)
        self._botao(g, "Comparar sem AA x SSAA na árvore", self.aa_arvore)
        lay.addStretch()
        return w

    def _aba_recorte(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        g = self._grupo(lay, "Demonstração")
        self._botao(g, "Exemplo numérico + cena de teste", self.recorte_demo)
        g = self._grupo(lay, "Aplicado à árvore carregada")
        g.addWidget(QLabel("Vista:"))
        self.r_vista = self._combo_vista()
        g.addWidget(self.r_vista)
        self.r_tam = self._spin(g, "Tamanho da imagem (px):", 64, 1200, 300)
        g.addWidget(QLabel("Janela de recorte (frações 0 a 1):"))
        self.r_janela = []
        for rotulo, ini in (("x0", 0.30), ("y0", 0.30), ("x1", 0.70), ("y1", 0.70)):
            g.addWidget(QLabel(rotulo))
            s = QDoubleSpinBox()
            s.setRange(0.0, 1.0)
            s.setSingleStep(0.05)
            s.setDecimals(2)
            s.setValue(ini)
            g.addWidget(s)
            self.r_janela.append(s)
        self._botao(g, "Recortar a árvore (3 algoritmos)", self.recorte_arvore)
        lay.addStretch()
        return w

    def _aba_recorte_poligonos(self):
        """Módulo 7: Sutherland-Hodgman (sutherland_hodgman, em recorte.py),
        com as figuras do didatico.py (subcomando recorte-poligonos)."""
        w = QWidget()
        lay = QVBoxLayout(w)
        g = self._grupo(lay, "Demonstração")
        self._botao(g, "Passo a passo (polígono convexo)", self.rp_passos)
        self._botao(g, "Caso côncavo (polígono em U)", self.rp_concavo)
        g = self._grupo(lay, "Aplicado à árvore carregada")
        g.addWidget(QLabel("Vista:"))
        self.rp_vista = self._combo_vista()
        g.addWidget(self.rp_vista)
        self.rp_tam = self._spin(g, "Tamanho da imagem (px):", 64, 1200, 300)
        g.addWidget(QLabel("Janela de recorte (frações 0 a 1):"))
        self.rp_janela = []
        for rotulo, ini in (("x0", 0.25), ("y0", 0.25), ("x1", 0.75), ("y1", 0.75)):
            g.addWidget(QLabel(rotulo))
            s = QDoubleSpinBox()
            s.setRange(0.0, 1.0)
            s.setSingleStep(0.05)
            s.setDecimals(2)
            s.setValue(ini)
            g.addWidget(s)
            self.rp_janela.append(s)
        self._botao(g, "Recortar e preencher estrela sobre a árvore", self.rp_arvore)
        lay.addStretch()
        return w

    # --------------------------------------------------------- ações didáticas
    def _args(self, vista, tamanho, **extra):
        return SimpleNamespace(arvore=self.caminho, vista=vista.currentData(),
                               tamanho=tamanho.value(), **extra)

    def bresenham_demo(self):
        def producao():
            D.imprimir_tabela(*D.EXEMPLO)
            return {"Octantes": D.fig_octantes(), "Exemplo": D.fig_exemplo()}
        self._executar("bresenham", producao)

    def bresenham_interativo(self):
        plt.close("all")
        try:
            self._demo = D.DemoInterativo()
        except Exception as exc:
            self._erro("Erro no modo interativo", exc)
            return
        canvas = self._mostrar_figuras({"Interativo": self._demo.fig})[0]
        # o clique é ligado ao canvas Qt (o do __init__ era um canvas Agg)
        canvas.mpl_connect("button_press_event", self._demo.clique)
        self.statusBar().showMessage("Clique na grade: 1º clique = início, 2º = fim.")

    def bresenham_arvore(self):
        if not self._exigir_modelo():
            return
        args = self._args(self.b_vista, self.b_tam)
        self._executar("bresenham --arvore",
                       lambda: {"Árvore (Bresenham)": D.demo_arvore(args)})

    def scanline_demo(self):
        def producao():
            D.imprimir_tabela_scanline(D.POLIGONO)
            return {"Scanline": D.fig_scanline_exemplo(D.POLIGONO)}
        self._executar("poligonos", producao)

    def scanline_arvore(self):
        if not self._exigir_modelo():
            return
        args = self._args(self.s_vista, self.s_tam)
        self._executar("poligonos --arvore",
                       lambda: {"Região de interesse": D.fig_scanline_roi(args)})

    def aa_demo(self):
        k = self.a_k.value()
        self._executar("antialiasing", lambda: {"Teste": D.fig_aa_teste(k)})

    def aa_arvore(self):
        if not self._exigir_modelo():
            return
        if self.a_ref.value() <= self.a_k.value():
            QMessageBox.information(
                self, "Parâmetros", "O fator da referência deve ser maior que k.")
            return
        args = self._args(self.a_vista, self.a_tam,
                          k=self.a_k.value(), ref=self.a_ref.value())
        self._executar("antialiasing --arvore",
                       lambda: {"Árvore": D.fig_aa_arvore(args)})

    def recorte_demo(self):
        def producao():
            D.imprimir_exemplo_recorte()
            return {"Cena de teste": D.fig_recorte_teste()}
        self._executar("recorte", producao)

    def recorte_arvore(self):
        if not self._exigir_modelo():
            return
        x0, y0, x1, y1 = (s.value() for s in self.r_janela)
        if x0 >= x1 or y0 >= y1:
            QMessageBox.information(
                self, "Janela inválida", "É preciso ter x0 < x1 e y0 < y1.")
            return
        args = self._args(self.r_vista, self.r_tam, janela=[x0, y0, x1, y1])
        self._executar("recorte --arvore",
                       lambda: {"Árvore": D.fig_recorte_arvore(args)})

    @staticmethod
    def _como_dict(resultado, titulo):
        """As fig_sh_* do didatico.py podem devolver uma Figure, uma lista
        ou um dict; a GUI precisa de {titulo: Figure}."""
        if isinstance(resultado, dict):
            return resultado
        if isinstance(resultado, (list, tuple)):
            return {f"{titulo} {i + 1}": f for i, f in enumerate(resultado)}
        return {titulo: resultado}

    def rp_passos(self):
        self._executar("recorte-poligonos",
                       lambda: self._como_dict(D.fig_sh_passos(), "Passo a passo"))

    def rp_concavo(self):
        self._executar("recorte-poligonos (côncavo)",
                       lambda: self._como_dict(D.fig_sh_concavo(), "Côncavo (U)"))

    def rp_arvore(self):
        if not self._exigir_modelo():
            return
        x0, y0, x1, y1 = (s.value() for s in self.rp_janela)
        if x0 >= x1 or y0 >= y1:
            QMessageBox.information(
                self, "Janela inválida", "É preciso ter x0 < x1 e y0 < y1.")
            return
        args = self._args(self.rp_vista, self.rp_tam, janela=[x0, y0, x1, y1])
        self._executar("recorte-poligonos --arvore",
                       lambda: self._como_dict(D.fig_sh_arvore(args), "Árvore"))

    # ------------------------------------------------- execução e exibição
    def _executar(self, rotulo, producao):
        """Roda 'producao' (que devolve {titulo: Figure}) capturando o que o
        didatico.py imprimiria no terminal e mostrando tudo na janela."""
        plt.close("all")
        buf = io.StringIO()
        figuras = None
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            with contextlib.redirect_stdout(buf):
                figuras = producao()
        except SystemExit as exc:          # didatico.py usa sys.exit(msg)
            buf.write(f"\n{exc}\n")
        except Exception:
            buf.write("\n" + traceback.format_exc())
        finally:
            QApplication.restoreOverrideCursor()
        self._console(f"$ {rotulo}\n{buf.getvalue()}")
        if figuras:
            self._mostrar_figuras(figuras)
            self.statusBar().showMessage(f"{rotulo}: pronto.")
        else:
            self.statusBar().showMessage(f"{rotulo}: falhou (veja o console).")

    def _mostrar_figuras(self, figuras):
        """Embute as Figures do matplotlib (uma aba por figura)."""
        while self.fig_tabs.count():
            antigo = self.fig_tabs.widget(0)
            self.fig_tabs.removeTab(0)
            antigo.deleteLater()
        self._figuras = list(figuras.values())
        canvases = []
        for titulo, fig in figuras.items():
            canvas = FigureCanvasQTAgg(fig)
            try:
                fig.set_layout_engine("tight")   # acompanha o redimensionamento
            except Exception:
                pass
            host = QWidget()
            lay = QVBoxLayout(host)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(NavigationToolbar2QT(canvas, host))
            lay.addWidget(canvas)
            self.fig_tabs.addTab(host, titulo)
            canvases.append(canvas)
        self.stack.setCurrentIndex(1)
        return canvases

    # ======================================================================
    def ao_mudar_aba(self, indice):
        if indice == self.ABA_CCO:
            self.stack.setCurrentIndex(0)
        elif self.fig_tabs.count():
            self.stack.setCurrentIndex(1)

    def closeEvent(self, evento):
        plt.close("all")
        self.plotter.close()
        super().closeEvent(evento)


def main():
    app = QApplication(sys.argv)
    janela = MainWindow()
    janela.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

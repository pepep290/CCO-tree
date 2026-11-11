# BCC327 – Computação Gráfica (Semestre 2026.2)

## Trabalho Prático 1 (TP1): Visualização Geométrica, Rasterização e Recorte de Árvores Arteriais CCO

## 1. Integrantes do Grupo

- João Pedro Silva Cruz - 23.2.4060
- Pedro Vítor Silva Cruz - 24.2.4086

## 2. Tecnologia Gráfica Utilizada

- **Linguagem:** Python 3.14.3
- **Visualização 3D:** PyVista / VTK (renderização OpenGL, interação com mouse e câmera).
- **Interface integrada:** PyQt5 + pyvistaqt.
- **Figuras didáticas:** Matplotlib.
- **Matemática e algoritmos:** NumPy e Python puro. As transformações, a rasterização, o preenchimento, o antialiasing por supersampling e os recortes são **implementação própria do grupo** (ver seção 9).

## 3. Dependências e Versões

| Biblioteca   | Versão                 | Uso                                                        |
|--------------|------------------------|------------------------------------------------------------|
| `numpy`      | 2.4.4                  | álgebra das matrizes e dos vetores                         |
| `pyvista`    | 0.49.2                 | leitura do VTK, malhas, tubos, janela 3D                   |
| `vtk`        | 9.7.2                  | motor de renderização (instalado junto com o PyVista)      |
| `matplotlib` | 3.10.8                 | figuras dos módulos didáticos e mapa de cores              |
| `PyQt5`      | 5.15.11                | interface gráfica integrada (`main_gui.py`)                |
| `pyvistaqt`  | 0.13.2                 | embute a janela 3D do PyVista no Qt                        |


O `visualizador.py` e o `didatico.py` funcionam sem o PyQt5 e o pyvistaqt, que só são necessários para o `main_gui.py`.

## 4. Instruções de Instalação

1. Descompacte a pasta do projeto (`CCO-tree`) no seu computador.
2. Abra o terminal na **raiz** do projeto (`CCO-tree`). Todos os comandos deste README são executados a partir dela.
3. (Recomendado) Crie e ative um ambiente virtual:

   ```
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```

4. Instale as dependências:

   ```
   pip install -r requirements.txt
   ```

## 5. Localização Esperada dos Arquivos VTK

Os modelos fornecidos pelo professor devem ficar na pasta `data/`:

```
CCO-tree
├── data/
│   ├── dados_modelos2D/
│   │   └── tree2D_Nterm008.vtk  (e demais arquivos)
│   └── dados_modelos3D/
│       └── tree3D_Nterm016.vtk  (e demais arquivos)
├── src/
└── ...
```

## 6. Comandos de Execução

Todos a partir da raiz do projeto.

### 6.1 Interface integrada 

```
python src/main_gui.py
```

Abas: **Árvore CCO**, **Bresenham**, **Scanline**, **Antialiasing**, **Recorte** (segmentos) e **Recorte de polígonos**. O botão **Abrir VTK...** carrega o modelo. As tabelas e estatísticas que, pela linha de comando, saem no terminal aparecem no console embutido na parte de baixo da janela.

### 6.2 Visualizador CCO (Módulos 1 e 2, antialiasing do VTK)

```
python src/visualizador.py data/dados_modelos3D/tree3D_Nterm016.vtk
python src/visualizador.py data/dados_modelos2D/tree2D_Nterm008.vtk --tema escuro
python src/visualizador.py ARQUIVO.vtk --info
```

Opções: `--modo linhas|tubos`, `--tema claro|escuro`, `--cmap NOME`, `--campo-raio NOME`, `--escala-raio X`, `--vista frontal|lateral|topo|isometrica`, `--ortografica`, `--trans X Y Z`, `--rot RX RY RZ`, `--escala S`, `--info`.

Figuras para o relatório, sem abrir janela:

```
python src/visualizador.py ARQUIVO.vtk --exportar-vistas figs/
python src/visualizador.py ARQUIVO.vtk --figura-projecoes figs/projecoes.png
```

### 6.3 Módulos didáticos (Módulos 3, 4, 5 e 6)

```
python src/didatico.py bresenham                  # 8 octantes + exemplo numérico
python src/didatico.py bresenham --interativo     # clique para escolher os extremos
python src/didatico.py bresenham --arvore ARQUIVO.vtk
python src/didatico.py poligonos                  # Scanline Fill em polígono côncavo
python src/didatico.py poligonos --arvore ARQUIVO.vtk
python src/didatico.py antialiasing               # sem AA x supersampling
python src/didatico.py antialiasing --arvore ARQUIVO.vtk --k 4 --ref 8
python src/didatico.py recorte                    # Cohen–Sutherland, Liang–Barsky, Cyrus–Beck
python src/didatico.py recorte --arvore ARQUIVO.vtk --janela 0.25 0.25 0.75 0.75
```

Em todos, `--salvar PASTA/` grava PNGs em vez de abrir janelas; `--vista` e `--tamanho` ajustam a projeção e a resolução da imagem.

### 6.4 Recorte de polígonos (Módulo 7)

O Sutherland–Hodgman está em `recorte.py` (função `sutherland_hodgman`) e as figuras saem pelo `didatico.py`, no subcomando `recorte-poligonos`. Não existe arquivo separado.

```
python src/didatico.py recorte-poligonos                     # passo a passo (convexo) e caso côncavo em U
python src/didatico.py recorte-poligonos --arvore ARQUIVO.vtk --janela 0.25 0.25 0.75 0.75
python src/didatico.py recorte-poligonos --salvar figs/
```

### 6.5 Autotestes dos algoritmos

```
python src/rasterizacao.py          # Bresenham (8 octantes) e Scanline Fill
python src/recorte.py               # Cohen–Sutherland x Liang–Barsky x Cyrus–Beck e Sutherland–Hodgman
```

## 7. Comandos de Teclado e Mouse

### Janela 3D (`visualizador.py` e aba "Árvore CCO" do `main_gui.py`)

**Mouse**

| Ação                     | Efeito          |
|--------------------------|-----------------|
| Botão esquerdo + arrastar | gira a câmera   |
| Botão direito ou roda    | zoom            |
| Botão do meio + arrastar | move (pan)      |


**Sliders do `visualizador.py`** (canto esquerdo da janela): translação em x, y e z (em % da diagonal do modelo, de −50 a 50), rotação em x, y e z (−180° a 180°) e escala (0,2 a 3,0).

### Interface integrada (`main_gui.py`)

Na aba "Árvore CCO", as mesmas funções ficam em controles: caixas de seleção (primitiva, vista, projeção ortográfica, antialiasing, cor por raio, tema), os mesmos sliders de transformação e botões para mostrar as matrizes M, V e P no console, exportar as 4 vistas × 2 projeções e gerar a figura ortográfica × perspectiva. As teclas acima **não** funcionam no `main_gui.py`; só o mouse.

### Modo interativo do Bresenham

`python src/didatico.py bresenham --interativo` (ou o botão correspondente no `main_gui.py`): 1º clique na grade define o início do segmento, 2º define o fim, 3º recomeça.

## 8. Roteiro Mínimo para Teste das Funcionalidades

Todos os comandos usam o modelo `data/dados_modelos3D/tree3D_Nterm016.vtk` (3D) ou `data/dados_modelos2D/tree2D_Nterm008.vtk` (2D). 

1. **Módulo 1 – Leitura, primitivas e atributos**
   - `python src/visualizador.py ARQUIVO.vtk --info` imprime número de pontos e segmentos, bounds, arrays disponíveis e raio mínimo e máximo.
   - Sem `--info`, abra a janela 3D: o canto inferior direito mostra as mesmas estatísticas, as cores seguem o raio (barra de cores à direita) e `6` alterna entre tubos e linhas.
2. **Módulo 2 – Transformações e observador**
   - Arraste os sliders de translação, rotação e escala; `8` zera tudo.
   - Teclas `1`, `2`, `4` e `5` mostram quatro vistas diferentes do observador.
   - Com um modelo 3D, `0` alterna perspectiva e ortográfica; `9` imprime M, V e P no terminal.
   - Figura comparativa: `python src/visualizador.py ARQUIVO.vtk --figura-projecoes figs/projecoes.png`.
3. **Módulo 3 – Rasterização de linhas**
   - `python src/didatico.py bresenham` imprime a tabela passo a passo e mostra os 8 octantes e o exemplo numérico.
   - `python src/didatico.py bresenham --arvore ARQUIVO.vtk` rasteriza a árvore e compara com o DDA.
4. **Módulo 4 – Rasterização de polígonos**
   - `python src/didatico.py poligonos` mostra o Scanline Fill num polígono côncavo, com a tabela de arestas e a varredura.
   - Com `--arvore ARQUIVO.vtk`, preenche uma região de interesse sobre a árvore.
5. **Módulo 5 – Aliasing e antialiasing**
   - `python src/didatico.py antialiasing` compara sem antialiasing e supersampling k×k (implementação do grupo), com erro quadrático médio.
   - Na janela 3D do visualizador, `F2` liga/desliga o antialiasing do VTK.
6. **Módulo 6 – Recorte de segmentos**
   - `python src/didatico.py recorte` mostra o exemplo numérico, a cena de teste antes e depois, e confere que os três algoritmos concordam.
   - Com `--arvore ARQUIVO.vtk --janela 0.25 0.25 0.75 0.75`, recorta a árvore.
7. **Módulo 7 – Recorte de polígonos**
   - `python src/didatico.py recorte-poligonos` mostra o Sutherland–Hodgman passo a passo num polígono convexo e o caso côncavo em U, com o trecho degenerado em vermelho: o caso em que o Weiler–Atherton é o algoritmo adequado.
   - Com `--arvore ARQUIVO.vtk --janela 0.25 0.25 0.75 0.75`, recorta uma estrela sobre a árvore e preenche o resultado com o Scanline do grupo.
8. **Interface integrada**
   - `python src/main_gui.py`, depois **Abrir VTK...** e percorrer as abas. Os botões de cada aba reproduzem os itens acima.
9. **Autotestes** – rodar os dois comandos da seção 6.5; todos terminam sem erro.

## 9. Declaração de Autoria e Funcionalidades

### Implementado pelo grupo (código próprio)

- **`modelo.py`**: extração dos segmentos a partir das linhas do VTK, detecção do atributo de raio, estatísticas (pontos, segmentos, raio mín/máx) e preparação do raio auxiliar dos tubos.
- **`transformacoes.py`**: matrizes 4×4 de translação, rotação (x, y, z), escala e modelo (M); matriz de vista (V, tipo *lookAt*); projeções ortográfica e perspectiva (P); divisão perspectiva e coordenadas NDC; vistas predefinidas.
- **`rasterizacao.py`**: algoritmo de Bresenham (8 octantes, aritmética inteira), DDA, transformação de viewport, framebuffer, rasterização da árvore projetada, **supersampling (antialiasing) próprio** com filtro de caixa e cálculo do erro quadrático médio, e **Scanline Fill** com tabela de arestas e lista de arestas ativas (regra par-ímpar, conta exata com frações).
- **`recorte.py`**: **Cohen–Sutherland**, **Liang–Barsky** e **Cyrus–Beck** de segmentos, e o **Sutherland–Hodgman** de polígonos (`sutherland_hodgman`, contra qualquer janela convexa) com detecção dos trechos degenerados em polígonos côncavos.
- **`didatico.py`**, **`visualizador.py`** e **`main_gui.py`**: orquestração, tabelas, figuras e interface (que chamam os módulos acima).

### Realizado com auxílio de bibliotecas

- **PyVista/VTK**: leitura do arquivo `.vtk`, renderização OpenGL, geração dos tubos (`tube`), widgets de slider, interação com o mouse, e o antialiasing do VTK ligado por `F2`. A matriz M é calculada pelo grupo, mas é o VTK que a multiplica pelos vértices na hora de desenhar; a posição da câmera vem das nossas vistas, e o VTK monta as suas próprias V e P para a janela 3D. As nossas V e P são usadas na rasterização, no antialiasing próprio e na figura de projeções.
- **Matplotlib**: desenho das figuras dos módulos didáticos e mapa contínuo de cores (`viridis`) usado na rasterização.
- **PyQt5 / pyvistaqt**: janela, abas, sliders e console da interface integrada.
- **NumPy**: operações com vetores e matrizes.


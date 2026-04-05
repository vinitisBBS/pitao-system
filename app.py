from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pistao-cidade-alta-secret-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pistao.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Faça login para acessar o sistema.'

# ─────────────────────────────────────────────
# MODELOS
# ─────────────────────────────────────────────

class Cargo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    nivel = db.Column(db.Integer, default=1)          # 100 = dono
    pode_ver_dashboard   = db.Column(db.Boolean, default=True)
    pode_ver_metas       = db.Column(db.Boolean, default=True)
    pode_adicionar_valor = db.Column(db.Boolean, default=False)
    pode_gerenciar_users = db.Column(db.Boolean, default=False)
    pode_gerenciar_metas = db.Column(db.Boolean, default=False)
    pode_gerenciar_cargos= db.Column(db.Boolean, default=False)
    cor                  = db.Column(db.String(10), default='#f5c518')
    usuarios = db.relationship('Usuario', backref='cargo', lazy=True)

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login    = db.Column(db.String(50), unique=True, nullable=False)
    senha    = db.Column(db.String(200), nullable=False)
    nome     = db.Column(db.String(100), nullable=False)
    cargo_id = db.Column(db.Integer, db.ForeignKey('cargo.id'), nullable=True)
    ativo    = db.Column(db.Boolean, default=True)
    criado_em= db.Column(db.DateTime, default=datetime.utcnow)
    valores  = db.relationship('ValorMeta', backref='usuario', lazy=True)

class Meta(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    titulo     = db.Column(db.String(200), nullable=False)
    descricao  = db.Column(db.Text, default='')
    valor_alvo = db.Column(db.Float, default=0)
    aberta     = db.Column(db.Boolean, default=True)
    criado_em  = db.Column(db.DateTime, default=datetime.utcnow)
    valores    = db.relationship('ValorMeta', backref='meta', lazy=True, cascade='all, delete-orphan')

class ValorMeta(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    meta_id    = db.Column(db.Integer, db.ForeignKey('meta.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    valor      = db.Column(db.Float, nullable=False)
    obs        = db.Column(db.String(300), default='')
    criado_em  = db.Column(db.DateTime, default=datetime.utcnow)

class StatusPistao(db.Model):
    id      = db.Column(db.Integer, primary_key=True)
    chave   = db.Column(db.String(50), unique=True)
    valor   = db.Column(db.Text, default='')

# ─────────────────────────────────────────────
# SEED INICIAL
# ─────────────────────────────────────────────

def seed():
    # Cargos padrão
    cargos_default = [
        {'nome': 'Dono',       'nivel': 100, 'cor': '#f5c518',
         'pode_ver_dashboard': True, 'pode_ver_metas': True,
         'pode_adicionar_valor': True, 'pode_gerenciar_users': True,
         'pode_gerenciar_metas': True, 'pode_gerenciar_cargos': True},
        {'nome': 'Gerente',    'nivel': 80,  'cor': '#e8a000',
         'pode_ver_dashboard': True, 'pode_ver_metas': True,
         'pode_adicionar_valor': True, 'pode_gerenciar_users': True,
         'pode_gerenciar_metas': True, 'pode_gerenciar_cargos': False},
        {'nome': 'Financeiro', 'nivel': 60,  'cor': '#39d96b',
         'pode_ver_dashboard': True, 'pode_ver_metas': True,
         'pode_adicionar_valor': True, 'pode_gerenciar_users': False,
         'pode_gerenciar_metas': True, 'pode_gerenciar_cargos': False},
        {'nome': 'Dybala',     'nivel': 40,  'cor': '#c96b00',
         'pode_ver_dashboard': True, 'pode_ver_metas': True,
         'pode_adicionar_valor': True, 'pode_gerenciar_users': False,
         'pode_gerenciar_metas': False, 'pode_gerenciar_cargos': False},
        {'nome': 'Pista',      'nivel': 20,  'cor': '#a0a0a0',
         'pode_ver_dashboard': True, 'pode_ver_metas': True,
         'pode_adicionar_valor': True, 'pode_gerenciar_users': False,
         'pode_gerenciar_metas': False, 'pode_gerenciar_cargos': False},
        {'nome': 'Membro',     'nivel': 10,  'cor': '#888888',
         'pode_ver_dashboard': True, 'pode_ver_metas': True,
         'pode_adicionar_valor': False, 'pode_gerenciar_users': False,
         'pode_gerenciar_metas': False, 'pode_gerenciar_cargos': False},
    ]
    for c in cargos_default:
        if not Cargo.query.filter_by(nome=c['nome']).first():
            db.session.add(Cargo(**c))
    db.session.commit()

    # Usuário Dono
    if not Usuario.query.filter_by(login='jn').first():
        cargo_dono = Cargo.query.filter_by(nome='Dono').first()
        dono = Usuario(
            login='jn',
            senha=generate_password_hash('@jn123'),
            nome='JN',
            cargo_id=cargo_dono.id,
            ativo=True
        )
        db.session.add(dono)
        db.session.commit()

    # Status padrão
    campos_status = ['status_geral', 'avisos', 'saldo_caixa']
    for c in campos_status:
        if not StatusPistao.query.filter_by(chave=c).first():
            db.session.add(StatusPistao(chave=c, valor=''))
    db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def dono_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.cargo or current_user.cargo.nivel < 100:
            flash('Acesso restrito ao Dono.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def perm_required(perm):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            cargo = current_user.cargo
            if not cargo or not getattr(cargo, perm, False):
                flash('Você não tem permissão para isso.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ─────────────────────────────────────────────
# ROTAS AUTH
# ─────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        login_val = request.form.get('login', '').strip()
        senha_val = request.form.get('senha', '')
        user = Usuario.query.filter_by(login=login_val, ativo=True).first()
        if user and check_password_hash(user.senha, senha_val):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Login ou senha incorretos.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    metas = Meta.query.filter_by(aberta=True).all()
    status = {s.chave: s.valor for s in StatusPistao.query.all()}
    total_membros = Usuario.query.filter_by(ativo=True).count()

    metas_data = []
    for meta in metas:
        total = sum(v.valor for v in meta.valores)
        progresso = (total / meta.valor_alvo * 100) if meta.valor_alvo > 0 else 0
        metas_data.append({
            'meta': meta,
            'total': total,
            'progresso': min(progresso, 100)
        })

    return render_template('dashboard.html',
        metas_data=metas_data,
        status=status,
        total_membros=total_membros
    )

# ─────────────────────────────────────────────
# METAS
# ─────────────────────────────────────────────

@app.route('/metas')
@login_required
def metas():
    todas = Meta.query.order_by(Meta.criado_em.desc()).all()
    return render_template('metas.html', metas=todas)

@app.route('/meta/criar', methods=['POST'])
@login_required
@perm_required('pode_gerenciar_metas')
def criar_meta():
    titulo = request.form.get('titulo', '').strip()
    descricao = request.form.get('descricao', '').strip()
    valor_alvo = float(request.form.get('valor_alvo', 0) or 0)
    if not titulo:
        flash('Título obrigatório.', 'error')
        return redirect(url_for('metas'))
    db.session.add(Meta(titulo=titulo, descricao=descricao, valor_alvo=valor_alvo))
    db.session.commit()
    flash('Meta criada com sucesso!', 'success')
    return redirect(url_for('metas'))

@app.route('/meta/<int:meta_id>/fechar', methods=['POST'])
@login_required
@perm_required('pode_gerenciar_metas')
def fechar_meta(meta_id):
    meta = Meta.query.get_or_404(meta_id)
    meta.aberta = False
    db.session.commit()
    flash('Meta fechada.', 'success')
    return redirect(url_for('metas'))

@app.route('/meta/<int:meta_id>/abrir', methods=['POST'])
@login_required
@perm_required('pode_gerenciar_metas')
def abrir_meta(meta_id):
    meta = Meta.query.get_or_404(meta_id)
    meta.aberta = True
    db.session.commit()
    flash('Meta reaberta.', 'success')
    return redirect(url_for('metas'))

@app.route('/meta/<int:meta_id>/deletar', methods=['POST'])
@login_required
@perm_required('pode_gerenciar_metas')
def deletar_meta(meta_id):
    meta = Meta.query.get_or_404(meta_id)
    db.session.delete(meta)
    db.session.commit()
    flash('Meta deletada.', 'success')
    return redirect(url_for('metas'))

@app.route('/meta/<int:meta_id>/adicionar', methods=['POST'])
@login_required
@perm_required('pode_adicionar_valor')
def adicionar_valor(meta_id):
    meta = Meta.query.get_or_404(meta_id)
    if not meta.aberta:
        flash('Essa meta está fechada.', 'error')
        return redirect(url_for('metas'))
    valor = float(request.form.get('valor', 0) or 0)
    obs   = request.form.get('obs', '').strip()
    if valor <= 0:
        flash('Valor inválido.', 'error')
        return redirect(url_for('metas'))
    db.session.add(ValorMeta(meta_id=meta_id, usuario_id=current_user.id, valor=valor, obs=obs))
    db.session.commit()
    flash(f'$ {valor:,.0f} adicionado à meta!', 'success')
    return redirect(url_for('metas'))

# ─────────────────────────────────────────────
# USUÁRIOS
# ─────────────────────────────────────────────

@app.route('/usuarios')
@login_required
@perm_required('pode_gerenciar_users')
def usuarios():
    todos = Usuario.query.order_by(Usuario.criado_em.desc()).all()
    cargos = Cargo.query.order_by(Cargo.nivel.desc()).all()
    return render_template('usuarios.html', usuarios=todos, cargos=cargos)

@app.route('/usuario/criar', methods=['POST'])
@login_required
@perm_required('pode_gerenciar_users')
def criar_usuario():
    login_val = request.form.get('login', '').strip()
    senha_val = request.form.get('senha', '').strip()
    nome_val  = request.form.get('nome', '').strip()
    cargo_id  = request.form.get('cargo_id')

    if not login_val or not senha_val or not nome_val:
        flash('Preencha todos os campos.', 'error')
        return redirect(url_for('usuarios'))
    if Usuario.query.filter_by(login=login_val).first():
        flash('Login já existe.', 'error')
        return redirect(url_for('usuarios'))

    novo = Usuario(
        login=login_val,
        senha=generate_password_hash(senha_val),
        nome=nome_val,
        cargo_id=int(cargo_id) if cargo_id else None
    )
    db.session.add(novo)
    db.session.commit()
    flash(f'Usuário {nome_val} criado!', 'success')
    return redirect(url_for('usuarios'))

@app.route('/usuario/<int:uid>/editar', methods=['POST'])
@login_required
@perm_required('pode_gerenciar_users')
def editar_usuario(uid):
    user = Usuario.query.get_or_404(uid)
    # Protege o dono de ser editado por outros
    if user.cargo and user.cargo.nivel == 100 and current_user.cargo.nivel < 100:
        flash('Não é possível editar o Dono.', 'error')
        return redirect(url_for('usuarios'))

    user.nome  = request.form.get('nome', user.nome).strip()
    cargo_id   = request.form.get('cargo_id')
    user.cargo_id = int(cargo_id) if cargo_id else None

    nova_senha = request.form.get('senha', '').strip()
    if nova_senha:
        user.senha = generate_password_hash(nova_senha)

    db.session.commit()
    flash('Usuário atualizado.', 'success')
    return redirect(url_for('usuarios'))

@app.route('/usuario/<int:uid>/toggle', methods=['POST'])
@login_required
@perm_required('pode_gerenciar_users')
def toggle_usuario(uid):
    user = Usuario.query.get_or_404(uid)
    if user.id == current_user.id:
        flash('Não pode desativar você mesmo.', 'error')
        return redirect(url_for('usuarios'))
    user.ativo = not user.ativo
    db.session.commit()
    flash('Status do usuário alterado.', 'success')
    return redirect(url_for('usuarios'))

# ─────────────────────────────────────────────
# CARGOS
# ─────────────────────────────────────────────

@app.route('/cargos')
@login_required
@perm_required('pode_gerenciar_cargos')
def cargos():
    todos = Cargo.query.order_by(Cargo.nivel.desc()).all()
    return render_template('cargos.html', cargos=todos)

@app.route('/cargo/criar', methods=['POST'])
@login_required
@perm_required('pode_gerenciar_cargos')
def criar_cargo():
    nome  = request.form.get('nome', '').strip()
    nivel = int(request.form.get('nivel', 10))
    cor   = request.form.get('cor', '#f5c518')
    if not nome:
        flash('Nome obrigatório.', 'error')
        return redirect(url_for('cargos'))
    if Cargo.query.filter_by(nome=nome).first():
        flash('Cargo já existe.', 'error')
        return redirect(url_for('cargos'))
    perms = {p: request.form.get(p) == 'on' for p in [
        'pode_ver_dashboard','pode_ver_metas','pode_adicionar_valor',
        'pode_gerenciar_users','pode_gerenciar_metas','pode_gerenciar_cargos']}
    db.session.add(Cargo(nome=nome, nivel=nivel, cor=cor, **perms))
    db.session.commit()
    flash(f'Cargo {nome} criado!', 'success')
    return redirect(url_for('cargos'))

@app.route('/cargo/<int:cid>/editar', methods=['POST'])
@login_required
@perm_required('pode_gerenciar_cargos')
def editar_cargo(cid):
    cargo = Cargo.query.get_or_404(cid)
    if cargo.nivel == 100 and current_user.cargo.nivel < 100:
        flash('Não é possível editar o cargo Dono.', 'error')
        return redirect(url_for('cargos'))
    cargo.nome  = request.form.get('nome', cargo.nome).strip()
    cargo.nivel = int(request.form.get('nivel', cargo.nivel))
    cargo.cor   = request.form.get('cor', cargo.cor)
    for p in ['pode_ver_dashboard','pode_ver_metas','pode_adicionar_valor',
              'pode_gerenciar_users','pode_gerenciar_metas','pode_gerenciar_cargos']:
        setattr(cargo, p, request.form.get(p) == 'on')
    db.session.commit()
    flash('Cargo atualizado!', 'success')
    return redirect(url_for('cargos'))

@app.route('/cargo/<int:cid>/deletar', methods=['POST'])
@login_required
@perm_required('pode_gerenciar_cargos')
def deletar_cargo(cid):
    cargo = Cargo.query.get_or_404(cid)
    if cargo.nivel == 100:
        flash('Não é possível deletar o cargo Dono.', 'error')
        return redirect(url_for('cargos'))
    # Remove referência de usuários
    for u in cargo.usuarios:
        u.cargo_id = None
    db.session.delete(cargo)
    db.session.commit()
    flash('Cargo deletado.', 'success')
    return redirect(url_for('cargos'))

# ─────────────────────────────────────────────
# STATUS PISTÃO (edição pelo dono)
# ─────────────────────────────────────────────

@app.route('/status/editar', methods=['POST'])
@login_required
@dono_required
def editar_status():
    for chave in ['status_geral', 'avisos', 'saldo_caixa']:
        s = StatusPistao.query.filter_by(chave=chave).first()
        if s:
            s.valor = request.form.get(chave, '').strip()
    db.session.commit()
    flash('Status da PISTÃO atualizado!', 'success')
    return redirect(url_for('dashboard'))

# ─────────────────────────────────────────────
# CALCULADORA
# ─────────────────────────────────────────────

@app.route('/calculadora')
@login_required
def calculadora():
    return render_template('calculadora.html')

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

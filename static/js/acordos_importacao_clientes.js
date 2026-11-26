(function () {
  'use strict';

  function parseClientes(texto) {
    return texto.split(/\r?\n/).map(function (linha) {
      linha = linha.trim();
      if (!linha) return null;

      var separador = linha.lastIndexOf('|');
      if (separador < 0) {
        return { nome: linha, nascimento: '' };
      }
      return {
        nome: linha.slice(0, separador).trim(),
        nascimento: linha.slice(separador + 1).trim()
      };
    }).filter(function (cliente) {
      return cliente;
    });
  }

  function normalizarNome(nome) {
    return nome.normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .trim()
      .replace(/\s+/g, ' ')
      .toLowerCase();
  }

  function paraDataBrasileira(data) {
    var partes = /^(\d{4})-(\d{2})-(\d{2})$/.exec(data);
    return partes ? partes[3] + '/' + partes[2] + '/' + partes[1] : '';
  }

  function inicializarEditor(editor) {
    var campoClientes = editor.querySelector('textarea[name$="-clientes"]');
    var lista = editor.querySelector('[data-client-list]');
    var campoNome = editor.querySelector('[data-new-client-name]');
    var campoNascimento = editor.querySelector('[data-new-client-birthdate]');
    var botaoAdicionar = editor.querySelector('[data-add-client]');
    var mensagem = editor.querySelector('[data-client-editor-message]');
    var armazenamento = editor.querySelector('[data-client-storage]');

    if (!campoClientes || !lista || !campoNome || !campoNascimento ||
        !botaoAdicionar || !mensagem || !armazenamento) {
      return;
    }

    function obterClientes() {
      return Array.from(lista.querySelectorAll('[data-client-item]'))
        .map(function (item) {
          return {
            nome: item.dataset.clientName || '',
            nascimento: item.dataset.clientBirthdate || ''
          };
        });
    }

    function sincronizarCampo() {
      campoClientes.value = obterClientes().map(function (cliente) {
        return cliente.nome + (cliente.nascimento
          ? ' | ' + cliente.nascimento
          : '');
      }).join('\n');
    }

    function atualizarListaVazia() {
      if (!lista.querySelector('[data-client-item]') &&
          !lista.querySelector('[data-no-clients]')) {
        var vazio = document.createElement('p');
        vazio.dataset.noClients = '';
        vazio.textContent = 'Nenhum cliente identificado.';
        lista.appendChild(vazio);
      }
    }

    function criarItem(cliente) {
      var item = document.createElement('div');
      item.className = 'clientes-importacao-item';
      item.dataset.clientItem = '';
      item.dataset.clientName = cliente.nome;
      item.dataset.clientBirthdate = cliente.nascimento;

      var nome = document.createElement('span');
      nome.className = 'clientes-importacao-nome';
      nome.textContent = (cliente.nome || '(nome não informado)') +
        (cliente.nascimento ? ' — ' + cliente.nascimento : '');

      var remover = document.createElement('button');
      remover.type = 'button';
      remover.className = 'clientes-importacao-remover';
      remover.dataset.removeClient = '';
      remover.setAttribute('aria-label', 'Remover ' + cliente.nome);
      remover.textContent = '×';
      remover.addEventListener('click', function () {
        item.remove();
        atualizarListaVazia();
        sincronizarCampo();
        mensagem.textContent = '';
      });

      item.appendChild(nome);
      item.appendChild(remover);
      return item;
    }

    function exibirClientes(clientes) {
      lista.replaceChildren();
      if (!clientes.length) {
        var vazio = document.createElement('p');
        vazio.dataset.noClients = '';
        vazio.textContent = 'Nenhum cliente identificado.';
        lista.appendChild(vazio);
        return;
      }
      clientes.forEach(function (cliente) {
        lista.appendChild(criarItem(cliente));
      });
    }

    function adicionarCliente() {
      var nome = campoNome.value.trim();
      if (!nome) {
        mensagem.textContent = 'Informe o nome do cliente.';
        campoNome.focus();
        return;
      }

      var nascimento = paraDataBrasileira(campoNascimento.value);
      var chave = normalizarNome(nome) + '|' + nascimento;
      var duplicado = obterClientes().some(function (cliente) {
        return normalizarNome(cliente.nome) + '|' + cliente.nascimento === chave;
      });
      if (duplicado) {
        mensagem.textContent = 'Esse cliente já está na lista.';
        campoNome.focus();
        return;
      }

      var vazio = lista.querySelector('[data-no-clients]');
      if (vazio) vazio.remove();
      lista.appendChild(criarItem({ nome: nome, nascimento: nascimento }));
      sincronizarCampo();
      campoNome.value = '';
      campoNascimento.value = '';
      mensagem.textContent = '';
      campoNome.focus();
    }

    exibirClientes(parseClientes(campoClientes.value));
    sincronizarCampo();
    armazenamento.hidden = true;
    botaoAdicionar.addEventListener('click', adicionarCliente);
    campoNome.addEventListener('keydown', function (evento) {
      if (evento.key === 'Enter') {
        evento.preventDefault();
        adicionarCliente();
      }
    });
  }

  function iniciar() {
    document.querySelectorAll('[data-client-editor]').forEach(inicializarEditor);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();

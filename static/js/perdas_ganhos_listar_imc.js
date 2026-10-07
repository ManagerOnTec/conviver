// calculos e legendas para o IMC em template perdas e ganhos
document.addEventListener('DOMContentLoaded', function () {
    var rows = document.querySelectorAll('.data-row');
    rows.forEach(function (row) {
        var pesoCell = row.querySelector('.peso');
        var alturaCell = row.querySelector('.altura');
        var statusCell = row.querySelector('.imc-status');

        var peso = parseFloat(pesoCell.textContent);
        var altura = parseFloat(alturaCell.textContent) / 100; // Convertendo cm para metros

        var imcValue = peso / (altura ** 2);

        var status = '';
        var color = '';

        if (imcValue < 18.5) {
            status = 'Abaixo do Peso';
            color = 'text-warning';
        } else if (imcValue >= 18.5 && imcValue < 24.9) {
            status = 'Normal';
            color = 'text-success';
        } else if (imcValue >= 25 && imcValue < 29.9) {
            status = 'Sobrepeso';
            color = 'text-warning';
        } else if (imcValue >= 30 && imcValue < 34.9) {
            status = 'Obesidade Grau 1';
            color = 'text-danger';
        } else if (imcValue >= 35 && imcValue < 39.9) {
            status = 'Obesidade Grau 2';
            color = 'text-danger';
        } else {
            status = 'Obesidade Grau 3';
            color = 'text-danger';
        }

        var span = document.createElement('span');
        span.className = color;
        span.textContent = status;
        statusCell.appendChild(span);
    });
});

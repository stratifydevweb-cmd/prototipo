function updateCode() {
    const nameSelect = document.getElementById('name');
    const codeInput = document.getElementById('code');
    const codes = {
        "PCR": "PCR001",
        "Antígeno": "ANT002",
        "Anticuerpos": "ANT003"
    };
    const selectedName = nameSelect.value;
    codeInput.value = codes[selectedName] || '';
}

document.addEventListener('DOMContentLoaded', function () {
    const ctx = document.getElementById('graficaEstadoAdmin');
    if (!ctx) {
        console.error("No se encontró el elemento con id 'graficaEstadoAdmin'");
        return;
    }

    // Usar datos globales pasados desde el template
    const datos = typeof datosGrafica !== 'undefined' ? datosGrafica : [];
    
    if (datos.length === 0) {
        ctx.parentElement.innerHTML = '<div class="text-center text-gray-500 py-8"><p>No hay datos disponibles para mostrar</p></div>';
        return;
    }

    const categorias = datos.map(item => item.categoria);
    const cantidades = datos.map(item => item.cantidad);

    // Colores profesionales con gradientes
    const coloresProfesionales = [
        {
            bg: 'rgba(59, 130, 246, 0.8)',
            border: 'rgba(59, 130, 246, 1)',
            gradient: ['rgba(59, 130, 246, 0.9)', 'rgba(37, 99, 235, 0.9)']
        },
        {
            bg: 'rgba(16, 185, 129, 0.8)',
            border: 'rgba(16, 185, 129, 1)',
            gradient: ['rgba(16, 185, 129, 0.9)', 'rgba(5, 150, 105, 0.9)']
        },
        {
            bg: 'rgba(139, 92, 246, 0.8)',
            border: 'rgba(139, 92, 246, 1)',
            gradient: ['rgba(139, 92, 246, 0.9)', 'rgba(124, 58, 237, 0.9)']
        },
        {
            bg: 'rgba(236, 72, 153, 0.8)',
            border: 'rgba(236, 72, 153, 1)',
            gradient: ['rgba(236, 72, 153, 0.9)', 'rgba(219, 39, 119, 0.9)']
        },
        {
            bg: 'rgba(251, 146, 60, 0.8)',
            border: 'rgba(251, 146, 60, 1)',
            gradient: ['rgba(251, 146, 60, 0.9)', 'rgba(249, 115, 22, 0.9)']
        },
        {
            bg: 'rgba(34, 197, 94, 0.8)',
            border: 'rgba(34, 197, 94, 1)',
            gradient: ['rgba(34, 197, 94, 0.9)', 'rgba(22, 163, 74, 0.9)']
        }
    ];

    // Crear gradientes para cada barra
    const gradients = categorias.map((_, index) => {
        const colorIndex = index % coloresProfesionales.length;
        const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, coloresProfesionales[colorIndex].gradient[0]);
        gradient.addColorStop(1, coloresProfesionales[colorIndex].gradient[1]);
        return gradient;
    });

    const graficaEstadoAdmin = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: categorias,
            datasets: [{
                label: 'Cantidad de Pruebas',
                data: cantidades,
                backgroundColor: categorias.map((_, index) => {
                    const colorIndex = index % coloresProfesionales.length;
                    return gradients[index] || coloresProfesionales[colorIndex].bg;
                }),
                borderColor: categorias.map((_, index) => {
                    const colorIndex = index % coloresProfesionales.length;
                    return coloresProfesionales[colorIndex].border;
                }),
                borderWidth: 2,
                borderRadius: 8,
                borderSkipped: false,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: {
                        size: 14,
                        weight: 'bold'
                    },
                    bodyFont: {
                        size: 13
                    },
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            const total = cantidades.reduce((a, b) => a + b, 0);
                            const porcentaje = ((context.parsed.y / total) * 100).toFixed(1);
                            return [
                                `Pruebas: ${context.parsed.y}`,
                                `Porcentaje: ${porcentaje}%`
                            ];
                        },
                        title: function(context) {
                            return `Categoría: ${context[0].label}`;
                        }
                    }
                },
                title: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        color: 'rgba(0, 0, 0, 0.6)',
                        font: {
                            size: 12,
                            weight: '500'
                        },
                        padding: 10
                    },
                    title: {
                        display: true,
                        text: 'Cantidad de Pruebas',
                        color: 'rgba(0, 0, 0, 0.7)',
                        font: {
                            size: 14,
                            weight: 'bold'
                        },
                        padding: {
                            bottom: 10
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: 'rgba(0, 0, 0, 0.6)',
                        font: {
                            size: 12,
                            weight: '500'
                        },
                        padding: 10
                    },
                    title: {
                        display: true,
                        text: 'Categorías de Pruebas',
                        color: 'rgba(0, 0, 0, 0.7)',
                        font: {
                            size: 14,
                            weight: 'bold'
                        },
                        padding: {
                            top: 10
                        }
                    }
                }
            },
            animation: {
                duration: 1500,
                easing: 'easeInOutQuart'
            }
        }
    });
});

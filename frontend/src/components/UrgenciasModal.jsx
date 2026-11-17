import { useState, useEffect } from 'react';

export default function UrgenciasModal() {
  // En producción, este estado lo dispararía el Rules Engine (R-13)
  const [visible, setVisible] = useState(false);

  // Simulación para mostrar el modal de prueba si se detecta dolor en el pecho
  window.triggerEmergencia = () => setVisible(true);

  if (!visible) return null;

  return (
    <div className="absolute inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl p-6 text-center shadow-2xl space-y-4 border-t-8 border-cuidacor-rojo">
        <h2 className="text-2xl font-bold text-cuidacor-rojo">Esto puede ser una emergencia</h2>
        <p className="text-gray-700 font-medium">Llama al 123 o ve a urgencias ahora.</p>
        <p className="text-sm text-gray-500">
          Si tienes dolor en el pecho, falta de aire repentina o desmayo, pide ayuda de inmediato.
        </p>
        <a href="tel:123" className="block w-full bg-cuidacor-rojo text-white py-3 rounded-xl font-bold text-lg">
          Llamar al 123
        </a>
        <button onClick={() => setVisible(false)} className="block w-full text-gray-500 py-2">
          Volver al inicio
        </button>
      </div>
    </div>
  );
}
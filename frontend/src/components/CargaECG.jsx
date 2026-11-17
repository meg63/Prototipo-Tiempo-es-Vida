import { useState } from 'react';

export default function CargaECG() {
  const [procesando, setProcesando] = useState(false);
  const [resultado, setResultado] = useState(null);

  const handleSubida = () => {
    setProcesando(true);
    // Simula la llamada al servicio de Django mockeado
    setTimeout(() => {
      setResultado({
        NORM: 0.85, MI: 0.05, STTC: 0.12, CD: 0.01, HYP: 0.02
      });
      setProcesando(false);
    }, 3000);
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-cuidacor-turquesa">Cargar ECG</h2>
      <p className="text-sm text-gray-600">Sube un caso de prueba para analizarlo. Señal digital compatible con PTB-XL.</p>
      
      {!resultado && (
        <div className="space-y-4">
          <input type="file" className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-cuidacor-menta file:text-cuidacor-turquesa" />
          <label className="flex items-start space-x-2 text-sm">
            <input type="checkbox" className="mt-1" required />
            <span>Entiendo que es un caso de prueba y no mi propio electrocardiograma</span>
          </label>
          <button 
            onClick={handleSubida} 
            disabled={procesando}
            className="w-full bg-cuidacor-turquesa text-white py-3 rounded-xl font-bold"
          >
            {procesando ? 'Procesando (meta < 3 min)...' : 'Enviar a análisis'}
          </button>
        </div>
      )}

      {resultado && (
        <div className="bg-white border rounded-xl p-4 space-y-3 shadow-sm">
          <h3 className="font-bold text-lg">Resultado experimental</h3>
          <ul className="space-y-2 text-sm">
            <li className="flex justify-between border-b pb-1"><span>NORM (Sin hallazgos)</span> <span>{resultado.NORM}</span></li>
            <li className="flex justify-between border-b pb-1"><span>MI (Patrón infarto)</span> <span>{resultado.MI}</span></li>
            <li className="flex justify-between border-b pb-1"><span>STTC (Cambios ST/T)</span> <span>{resultado.STTC}</span></li>
            <li className="flex justify-between border-b pb-1"><span>CD (Conducción)</span> <span>{resultado.CD}</span></li>
            <li className="flex justify-between"><span>HYP (Hipertrofia)</span> <span>{resultado.HYP}</span></li>
          </ul>
          <p className="text-xs text-gray-500 mt-4 bg-gray-50 p-2 rounded">
            Resultado experimental con datos de PTB-XL. No es un diagnóstico. Si tiene síntomas, consulte a un profesional de salud.
          </p>
          <button onClick={() => setResultado(null)} className="w-full border border-cuidacor-turquesa text-cuidacor-turquesa py-2 rounded-xl mt-4">
            Cargar otro ECG
          </button>
        </div>
      )}
    </div>
  );
}
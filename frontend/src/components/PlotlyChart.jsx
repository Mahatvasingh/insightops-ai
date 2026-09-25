import React, { useEffect, useRef } from 'react';

export default function PlotlyChart({ spec, height = 350 }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (window.Plotly && containerRef.current && spec) {
      const data = spec.data || [];
      const layout = {
        autosize: true,
        height: height,
        margin: { t: 40, r: 30, l: 40, b: 40 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#94a3b8', family: 'Plus Jakarta Sans, sans-serif' },
        xaxis: { gridcolor: '#1e293b', zerolinecolor: '#334155' },
        yaxis: { gridcolor: '#1e293b', zerolinecolor: '#334155' },
        ...(spec.layout || {})
      };

      const config = { responsive: true, displayModeBar: false };

      window.Plotly.newPlot(containerRef.current, data, layout, config);
    }
  }, [spec, height]);

  if (!spec) {
    return <div className="h-48 flex items-center justify-center text-xs text-slate-500">No chart data generated</div>;
  }

  return <div ref={containerRef} className="w-full" style={{ minHeight: `${height}px` }} />;
}

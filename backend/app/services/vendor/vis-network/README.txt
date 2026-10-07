vis-network 9.1.9（npm: vis-network@9.1.9，dist/vis-network.min.js、dist/dist/vis-network.min.css）
用途：knowledge_graph_generator.py 產生 graph.html 時直接內嵌，不再從 unpkg CDN 載入（2026-10-07）。
min.js 已移除最後一行 sourceMappingURL（內嵌後無對應 .map，避免瀏覽器 404）。
授權：Apache-2.0 OR MIT（見同目錄 LICENSE 檔）。升級版本時請整組替換並更新本檔。

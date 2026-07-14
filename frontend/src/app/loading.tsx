// Next.js route-level loading UI — shown while page.tsx hydrates.
// Keeps the screen from showing a blank white/black flash.
export default function Loading() {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#ffffff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div style={{ textAlign: "center" }}>
        <div style={{
          width: "32px",
          height: "32px",
          borderRadius: "8px",
          background: "linear-gradient(135deg, #203eec 0%, #00d4ff 100%)",
          margin: "0 auto 16px",
          animation: "cube-spin 1.2s linear infinite",
        }} />
        <p style={{
          fontSize: "11px",
          letterSpacing: "0.14em",
          textTransform: "uppercase",
          color: "rgba(0,0,0,0.3)",
          fontFamily: "system-ui, sans-serif",
          fontWeight: 600,
        }}>
          Cortex
        </p>
      </div>
    </div>
  )
}

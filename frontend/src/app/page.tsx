'use client';

import { useEffect, useRef } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const RepoTreeLazy = dynamic(
  () => import('@/features/tree/RepoTree'),
  { ssr: false, loading: () => <div style={{ width:'100%', height:'100%' }} /> }
);

export default function LandingPage() {
  const progressRef = useRef(0);

  useEffect(() => {
    // ── GSAP ScrollTrigger — pins hero, drives tree progress ──
    const heroEl = document.getElementById('hero-pin');
    if (heroEl) {
      ScrollTrigger.create({
        trigger: heroEl,
        start: 'top top',
        end: '+=280%',
        pin: true,
        pinSpacing: true,
        scrub: 1.2,
        onUpdate: (self) => {
          progressRef.current = self.progress;
          // Fade hero copy out after 65% scroll
          const copy = document.getElementById('hero-copy-left');
          if (copy) {
            const opacity = self.progress < 0.5 ? 1 : Math.max(0, 1 - (self.progress - 0.5) / 0.25);
            copy.style.opacity = String(opacity);
            copy.style.transform = `translateY(${(1 - opacity) * -24}px)`;
          }
        },
      });
    }

    // ── Intersection Observer for all other scroll reveals ──
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) entry.target.classList.add('revealed');
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -60px 0px' }
    );
    document
      .querySelectorAll('[data-reveal], [data-stagger]')
      .forEach((el) => observer.observe(el));

    // ── Cycling headline word ──
    const words = ['Code.', 'Systems.', 'Architecture.', 'Patterns.', 'Everything.'];
    let idx = 0;
    const cycleEl = document.getElementById('cycle-word') as HTMLElement | null;
    if (cycleEl) {
      cycleEl.textContent = words[0];
      cycleEl.style.cssText = `
        display: inline-block;
        background: linear-gradient(135deg, #7C3AED, #22D3EE, #34D399);
        background-size: 200% 200%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: gradient-shift 4s ease infinite;
        transition: opacity 0.25s ease, transform 0.25s ease;
      `;
    }
    const cycle = setInterval(() => {
      if (!cycleEl) return;
      cycleEl.style.opacity = '0';
      cycleEl.style.transform = 'translateY(12px)';
      setTimeout(() => {
        idx = (idx + 1) % words.length;
        cycleEl.textContent = words[idx];
        cycleEl.style.opacity = '1';
        cycleEl.style.transform = 'translateY(0)';
      }, 260);
    }, 2800);

    // ── Parallax on hero orbs ──
    const handleScroll = () => {
      const y = window.scrollY;
      document.querySelectorAll<HTMLElement>('.parallax-orb').forEach((orb, i) => {
        orb.style.transform = `translateY(${y * (0.08 + i * 0.04)}px)`;
      });
    };
    window.addEventListener('scroll', handleScroll, { passive: true });

    // ── Number counter animation ──
    const counters = document.querySelectorAll<HTMLElement>('[data-count]');
    const countObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const target = entry.target as HTMLElement;
          const end = parseInt(target.dataset.count ?? '0', 10);
          const duration = 1800;
          const startTime = performance.now();
          const update = (now: number) => {
            const p = Math.min((now - startTime) / duration, 1);
            const eased = 1 - Math.pow(1 - p, 3);
            target.textContent = Math.round(eased * end).toString();
            if (p < 1) requestAnimationFrame(update);
          };
          requestAnimationFrame(update);
          countObserver.unobserve(target);
        });
      },
      { threshold: 0.5 }
    );
    counters.forEach((c) => countObserver.observe(c));

    return () => {
      observer.disconnect();
      countObserver.disconnect();
      clearInterval(cycle);
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  return (
    <main style={{ background: '#000', color: '#fff' }}>

      {/* ── NAVBAR ── */}
      <nav className="cortex-nav">
        <div style={{ display:'flex', alignItems:'center', gap:'10px' }}>
          <div style={{ width:'24px', height:'24px', background:'linear-gradient(135deg,#7C3AED,#22D3EE)', borderRadius:'6px', animation:'spin-slow 10s linear infinite', flexShrink:0 }} />
          <span style={{ fontSize:'16px', fontWeight:500, color:'#fff' }}>Cortex</span>
          <span style={{ fontSize:'11px', color:'#52525B', padding:'2px 8px', border:'1px solid rgba(255,255,255,0.08)', borderRadius:'100px', marginLeft:'4px' }}>v0.1</span>
        </div>
        <div style={{ display:'flex', gap:'32px', position:'absolute', left:'50%', transform:'translateX(-50%)' }}>
          {['Features','How it works','Tech stack'].map((label) => (
            <a key={label} href={`#${label.toLowerCase().replace(/ /g,'-')}`}
              style={{ fontSize:'14px', color:'#A1A1AA', textDecoration:'none', transition:'color 0.2s' }}
              onMouseEnter={(e) => (e.currentTarget.style.color='#fff')}
              onMouseLeave={(e) => (e.currentTarget.style.color='#A1A1AA')}
            >{label}</a>
          ))}
        </div>
        <div style={{ display:'flex', gap:'12px', alignItems:'center' }}>
          <a href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
            style={{ fontSize:'14px', color:'#A1A1AA', textDecoration:'none', transition:'color 0.2s' }}
            onMouseEnter={(e) => (e.currentTarget.style.color='#fff')}
            onMouseLeave={(e) => (e.currentTarget.style.color='#A1A1AA')}
          >GitHub ↗</a>
          <Link href="/dashboard" style={{ fontSize:'14px', fontWeight:500, color:'#fff', background:'#7C3AED', padding:'8px 20px', borderRadius:'10px', textDecoration:'none', transition:'all 0.2s' }}
            onMouseEnter={(e) => { e.currentTarget.style.background='#6D28D9'; e.currentTarget.style.boxShadow='0 0 24px rgba(124,58,237,0.5)'; e.currentTarget.style.transform='translateY(-1px)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background='#7C3AED'; e.currentTarget.style.boxShadow='none'; e.currentTarget.style.transform='translateY(0)'; }}
          >Launch App →</Link>
        </div>
      </nav>

      {/* ── SECTION 1: HERO ── */}
      <section className="section-full" id="hero" style={{ background:'#000', paddingTop:'56px' }}>
        <div style={{ position:'absolute', inset:0, zIndex:0, backgroundImage:'linear-gradient(rgba(124,58,237,0.04) 1px,transparent 1px),linear-gradient(90deg,rgba(124,58,237,0.04) 1px,transparent 1px)', backgroundSize:'72px 72px' }} />
        <div className="parallax-orb" style={{ position:'absolute', zIndex:0, width:'700px', height:'700px', borderRadius:'50%', background:'radial-gradient(circle,rgba(124,58,237,0.14) 0%,transparent 65%)', filter:'blur(40px)', top:'-100px', left:'-100px', animation:'pulse-glow 8s ease-in-out infinite' }} />
        <div className="parallax-orb" style={{ position:'absolute', zIndex:0, width:'500px', height:'500px', borderRadius:'50%', background:'radial-gradient(circle,rgba(34,211,238,0.08) 0%,transparent 65%)', filter:'blur(60px)', top:'20%', right:'-100px', animation:'pulse-glow 12s ease-in-out infinite 4s' }} />
        <div className="parallax-orb" style={{ position:'absolute', zIndex:0, width:'400px', height:'400px', borderRadius:'50%', background:'radial-gradient(circle,rgba(52,211,153,0.06) 0%,transparent 65%)', filter:'blur(50px)', bottom:'-50px', left:'30%', animation:'pulse-glow 10s ease-in-out infinite 2s' }} />
        <div className="content-max" style={{ position:'relative', zIndex:1, display:'grid', gridTemplateColumns:'1fr 1fr', gap:'80px', alignItems:'center' }}>
          <div>
            <div data-reveal="up" style={{ display:'inline-flex', alignItems:'center', gap:'8px', padding:'6px 16px', border:'1px solid rgba(124,58,237,0.35)', borderRadius:'100px', background:'rgba(124,58,237,0.08)', marginBottom:'32px' }}>
              <div style={{ width:'6px', height:'6px', borderRadius:'50%', background:'#7C3AED', boxShadow:'0 0 8px #7C3AED', animation:'pulse-glow 2s ease-in-out infinite' }} />
              <span style={{ fontSize:'11px', fontWeight:500, letterSpacing:'0.14em', textTransform:'uppercase', color:'#A78BFA' }}>Engineering Reasoning Engine</span>
            </div>
            <h1 data-reveal="up" style={{ fontSize:'clamp(52px,7vw,100px)', fontWeight:300, letterSpacing:'-0.04em', lineHeight:0.92, color:'#fff', marginBottom:'28px' }}>
              Understand<br /><span id="cycle-word" />
            </h1>
            <p data-reveal="up" style={{ fontSize:'18px', lineHeight:1.7, color:'#A1A1AA', marginBottom:'40px', maxWidth:'460px' }}>
              Paste any GitHub URL. Cortex builds a knowledge graph of your codebase and generates architecture diagrams, learning paths, and interview prep — fully offline, zero API keys.
            </p>
            <div data-reveal="up" style={{ display:'flex', gap:'12px', flexWrap:'wrap' }}>
              <Link href="/dashboard" style={{ display:'inline-flex', alignItems:'center', gap:'8px', background:'#7C3AED', color:'#fff', fontSize:'15px', fontWeight:500, padding:'14px 28px', borderRadius:'12px', textDecoration:'none', transition:'all 0.25s' }}
                onMouseEnter={(e) => { e.currentTarget.style.background='#6D28D9'; e.currentTarget.style.boxShadow='0 8px 32px rgba(124,58,237,0.45)'; e.currentTarget.style.transform='translateY(-2px)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background='#7C3AED'; e.currentTarget.style.boxShadow='none'; e.currentTarget.style.transform='translateY(0)'; }}
              >Analyze a Repository <span style={{ fontSize:'18px' }}>→</span></Link>
              <a href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
                style={{ display:'inline-flex', alignItems:'center', gap:'8px', color:'#A1A1AA', fontSize:'15px', fontWeight:500, padding:'14px 28px', borderRadius:'12px', border:'1px solid rgba(255,255,255,0.1)', textDecoration:'none', transition:'all 0.25s' }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor='rgba(255,255,255,0.25)'; e.currentTarget.style.color='#fff'; e.currentTarget.style.transform='translateY(-2px)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor='rgba(255,255,255,0.1)'; e.currentTarget.style.color='#A1A1AA'; e.currentTarget.style.transform='translateY(0)'; }}
              >View Source ↗</a>
            </div>
            <div data-stagger style={{ display:'flex', gap:'40px', marginTop:'56px', paddingTop:'32px', borderTop:'1px solid rgba(255,255,255,0.06)' }}>
              {[{value:'6',label:'Artifact Types'},{value:'0',label:'API Keys Required'},{value:'∞',label:'Repos Supported'}].map(({value,label}) => (
                <div key={label}>
                  <div style={{ fontSize:'36px', fontWeight:200, letterSpacing:'-0.02em', color:'#fff' }}>{value}</div>
                  <div style={{ fontSize:'12px', color:'#52525B', marginTop:'4px' }}>{label}</div>
                </div>
              ))}
            </div>
          </div>
          <div data-reveal="scale" style={{ height:'580px', position:'relative' }}>
            <RepoTreeLazy />
            <div style={{ position:'absolute', bottom:0, left:0, right:0, height:'120px', background:'linear-gradient(to top,#000 0%,transparent 100%)', pointerEvents:'none' }} />
          </div>
        </div>
        <div style={{ position:'absolute', bottom:'32px', left:'50%', transform:'translateX(-50%)', display:'flex', flexDirection:'column', alignItems:'center', gap:'8px', animation:'float-medium 2.5s ease-in-out infinite' }}>
          <div style={{ width:'1px', height:'40px', background:'linear-gradient(to bottom,transparent,rgba(255,255,255,0.3))' }} />
          <span style={{ fontSize:'10px', color:'#52525B', letterSpacing:'0.12em', textTransform:'uppercase' }}>Scroll</span>
        </div>
      </section>

      {/* ── SECTION 2: HOW IT WORKS ── */}
      <section id="how-it-works" className="section-full" style={{ background:'linear-gradient(180deg,#000 0%,#050507 100%)' }}>
        <div className="content-max" style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'80px', alignItems:'center' }}>
          <div>
            <div data-reveal="up" style={{ fontSize:'11px', fontWeight:500, letterSpacing:'0.16em', textTransform:'uppercase', color:'#52525B', marginBottom:'20px' }}>01 / How it works</div>
            <h2 data-reveal="up" style={{ fontSize:'clamp(36px,5vw,64px)', fontWeight:300, letterSpacing:'-0.03em', color:'#fff', lineHeight:1.05, marginBottom:'56px' }}>
              Three steps.<br /><span style={{ color:'#52525B' }}>That&apos;s it.</span>
            </h2>
            <div data-stagger style={{ display:'flex', flexDirection:'column', gap:'0px' }}>
              {[
                { n:'01', title:'Paste a GitHub URL', desc:'Any public repository. Private repos coming soon.', color:'#7C3AED' },
                { n:'02', title:'Choose your artifact', desc:'Architecture diagram, learning path, API spec, interview prep — or all six.', color:'#22D3EE' },
                { n:'03', title:'Read your analysis', desc:'Generated in seconds using AST parsing and graph analysis. No LLM costs.', color:'#34D399' },
              ].map(({ n, title, desc, color }, i) => (
                <div key={n} style={{ display:'flex', gap:'24px', padding:'28px 0', borderBottom: i < 2 ? '1px solid rgba(255,255,255,0.06)' : 'none' }}>
                  <div style={{ fontSize:'12px', fontFamily:'monospace', color, fontWeight:500, minWidth:'28px', paddingTop:'2px' }}>{n}</div>
                  <div>
                    <div style={{ fontSize:'17px', fontWeight:400, color:'#fff', marginBottom:'6px' }}>{title}</div>
                    <div style={{ fontSize:'14px', color:'#71717A', lineHeight:1.6 }}>{desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div data-reveal="right">
            <div className="terminal">
              <div className="terminal-bar">
                <div className="dot-red" /><div className="dot-yellow" /><div className="dot-green" />
                <span style={{ fontFamily:'monospace', fontSize:'12px', color:'#52525B', marginLeft:'12px' }}>cortex — analysis engine</span>
              </div>
              <div className="terminal-body">
                <div className="t-muted">$ cortex analyze github.com/SUDHEER-KANDURU/DoseBuddy</div>
                <div className="t-violet">✦ Fetching repository structure...</div>
                <div className="t-white">&nbsp;&nbsp;→ Found 52 files across 8 modules</div>
                <div className="t-violet">✦ Running AST parser...</div>
                <div className="t-white">&nbsp;&nbsp;→ 847 functions, 23 classes indexed</div>
                <div className="t-violet">✦ Building Neo4j knowledge graph...</div>
                <div className="t-white">&nbsp;&nbsp;→ 156 nodes, 289 relationships</div>
                <div className="t-violet">✦ Generating artifacts...</div>
                <br />
                <div className="t-green">&nbsp;&nbsp;✓ architecture_diagram.mermaid</div>
                <div className="t-green">&nbsp;&nbsp;✓ module_breakdown.md</div>
                <div className="t-green">&nbsp;&nbsp;✓ learning_path.md</div>
                <div className="t-green">&nbsp;&nbsp;✓ interview_questions.md</div>
                <br />
                <div className="t-cyan">&nbsp;&nbsp;━━━ Completed in 2.8s ━━━</div>
                <div className="t-muted">$ <span className="t-cursor" /></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 3: FEATURES BENTO GRID ── */}
      <section id="features" style={{ background:'#050507', padding:'120px 0' }}>
        <div className="content-max">
          <div style={{ textAlign:'center', marginBottom:'64px' }}>
            <div data-reveal="up" style={{ fontSize:'11px', fontWeight:500, letterSpacing:'0.16em', textTransform:'uppercase', color:'#52525B', marginBottom:'16px' }}>02 / What you get</div>
            <h2 data-reveal="up" style={{ fontSize:'clamp(36px,5vw,72px)', fontWeight:300, letterSpacing:'-0.03em', color:'#fff', lineHeight:1.0 }}>
              Six artifacts.<br /><span style={{ color:'#52525B' }}>One repository.</span>
            </h2>
          </div>
          <div data-stagger className="bento-grid">
            <div className="bento-cell bento-wide" style={{ background:'linear-gradient(135deg,#0D0A1E,#0A0A0A)', borderColor:'rgba(124,58,237,0.2)', minHeight:'260px' }}>
              <div style={{ position:'absolute', top:'-60px', right:'-60px', width:'250px', height:'250px', borderRadius:'50%', background:'radial-gradient(circle,rgba(124,58,237,0.12),transparent)', filter:'blur(40px)' }} />
              <div style={{ fontSize:'11px', color:'#A78BFA', letterSpacing:'0.14em', textTransform:'uppercase', marginBottom:'14px' }}>Architecture Diagram</div>
              <div style={{ fontSize:'24px', fontWeight:300, color:'#fff', marginBottom:'16px', lineHeight:1.2 }}>See your entire<br />codebase as a graph</div>
              <div style={{ fontFamily:'monospace', fontSize:'12px', color:'#52525B', lineHeight:1.9, background:'rgba(0,0,0,0.4)', padding:'16px', borderRadius:'10px', border:'1px solid rgba(255,255,255,0.04)', display:'inline-block' }}>
                <span style={{ color:'#A78BFA' }}>graph</span> <span style={{ color:'#22D3EE' }}>LR</span><br />
                {'  '}A[API Gateway] <span style={{ color:'#34D399' }}>{'-->'}</span> B[Service Layer]<br />
                {'  '}B <span style={{ color:'#34D399' }}>{'-->'}</span> C[(PostgreSQL)]<br />
                {'  '}B <span style={{ color:'#34D399' }}>{'-->'}</span> D[(Redis Cache)]
              </div>
            </div>
            <div className="bento-cell" style={{ background:'linear-gradient(135deg,#0A1A0F,#0A0A0A)', borderColor:'rgba(52,211,153,0.2)', minHeight:'260px' }}>
              <div style={{ fontSize:'11px', color:'#34D399', letterSpacing:'0.14em', textTransform:'uppercase', marginBottom:'14px' }}>Learning Path</div>
              <div style={{ fontSize:'22px', fontWeight:300, color:'#fff', lineHeight:1.3 }}>Personalized curriculum<br />from your actual code</div>
              <div style={{ marginTop:'24px', display:'flex', flexDirection:'column', gap:'8px' }}>
                {['Week 1: Java fundamentals','Week 2: Spring Boot','Week 3: REST APIs'].map((w) => (
                  <div key={w} style={{ fontSize:'12px', color:'#52525B', display:'flex', alignItems:'center', gap:'8px' }}>
                    <div style={{ width:'6px', height:'6px', borderRadius:'50%', background:'#34D399', flexShrink:0 }} />{w}
                  </div>
                ))}
              </div>
            </div>
            <div className="bento-cell" style={{ background:'linear-gradient(135deg,#1A0A0A,#0A0A0A)', borderColor:'rgba(251,146,60,0.2)' }}>
              <div style={{ fontSize:'11px', color:'#FB923C', letterSpacing:'0.14em', textTransform:'uppercase', marginBottom:'14px' }}>Vibe Code Detection</div>
              <div style={{ fontSize:'20px', fontWeight:300, color:'#fff', lineHeight:1.3, marginBottom:'20px' }}>Flags AI-generated patterns before they ship</div>
              <div style={{ display:'flex', flexDirection:'column', gap:'6px' }}>
                {['No error handling detected','Duplicate logic in 3 files','Inconsistent naming found'].map((flag) => (
                  <div key={flag} style={{ fontSize:'12px', color:'#71717A', display:'flex', alignItems:'center', gap:'8px', padding:'8px 12px', background:'rgba(251,146,60,0.05)', border:'1px solid rgba(251,146,60,0.1)', borderRadius:'8px' }}>
                    <span style={{ color:'#FB923C' }}>⚠</span>{flag}
                  </div>
                ))}
              </div>
            </div>
            <div className="bento-cell" style={{ background:'linear-gradient(135deg,#0A0F1A,#0A0A0A)', borderColor:'rgba(34,211,238,0.2)' }}>
              <div style={{ fontSize:'11px', color:'#22D3EE', letterSpacing:'0.14em', textTransform:'uppercase', marginBottom:'14px' }}>Module Breakdown</div>
              <div style={{ fontSize:'20px', fontWeight:300, color:'#fff', lineHeight:1.3 }}>Logical modules with complexity scores</div>
            </div>
            <div className="bento-cell" style={{ background:'linear-gradient(135deg,#0D0A1E,#0A0A0A)', borderColor:'rgba(124,58,237,0.2)' }}>
              <div style={{ fontSize:'11px', color:'#A78BFA', letterSpacing:'0.14em', textTransform:'uppercase', marginBottom:'14px' }}>API Specification</div>
              <div style={{ fontSize:'20px', fontWeight:300, color:'#fff', lineHeight:1.3 }}>Structured reference from your controllers</div>
            </div>
            <div className="bento-cell bento-wide" style={{ background:'linear-gradient(135deg,#0A1510,#0A0A0A)', borderColor:'rgba(52,211,153,0.15)', display:'flex', alignItems:'center', justifyContent:'space-between' }}>
              <div>
                <div style={{ fontSize:'11px', color:'#34D399', letterSpacing:'0.14em', textTransform:'uppercase', marginBottom:'14px' }}>Interview Prep</div>
                <div style={{ fontSize:'24px', fontWeight:300, color:'#fff', lineHeight:1.2 }}>10 questions from<br />your actual project</div>
                <div style={{ fontSize:'14px', color:'#52525B', marginTop:'12px' }}>Walk into any interview fully prepared.</div>
              </div>
              <div style={{ fontSize:'72px', fontWeight:200, color:'rgba(52,211,153,0.1)', letterSpacing:'-0.04em', flexShrink:0 }}>Q&amp;A</div>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 4: STATS ── */}
      <section className="section-full" style={{ background:'#000', textAlign:'center' }}>
        <div className="content-max">
          <div data-reveal="up" style={{ fontSize:'11px', fontWeight:500, letterSpacing:'0.16em', textTransform:'uppercase', color:'#52525B', marginBottom:'64px' }}>By the numbers</div>
          <div data-stagger style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:'0px' }}>
            {[
              { count:6,   suffix:'',  label:'Artifact types generated' },
              { count:0,   suffix:'',  label:'External API calls required' },
              { count:100, suffix:'%', label:'Offline — no cloud needed' },
              { count:3,   suffix:'s', label:'Average analysis time' },
            ].map(({ count, suffix, label }, i) => (
              <div key={label} style={{ padding:'48px 32px', borderRight: i < 3 ? '1px solid rgba(255,255,255,0.06)' : 'none' }}>
                <div style={{ fontSize:'clamp(48px,6vw,80px)', fontWeight:200, letterSpacing:'-0.04em', color:'#fff', display:'flex', justifyContent:'center', alignItems:'baseline', gap:'4px' }}>
                  <span data-count={count}>0</span>
                  <span style={{ fontSize:'0.5em', color:'#A78BFA' }}>{suffix}</span>
                </div>
                <div style={{ fontSize:'14px', color:'#52525B', marginTop:'12px' }}>{label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── SECTION 5: SPLIT FEATURE ── */}
      <section className="section-full" style={{ background:'linear-gradient(180deg,#050507 0%,#000 100%)' }}>
        <div className="content-max" style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'80px', alignItems:'center' }}>
          <div>
            <div data-reveal="up" style={{ fontSize:'11px', fontWeight:500, letterSpacing:'0.16em', textTransform:'uppercase', color:'#52525B', marginBottom:'20px' }}>03 / Zero dependencies</div>
            <h2 data-reveal="up" style={{ fontSize:'clamp(36px,4.5vw,64px)', fontWeight:300, letterSpacing:'-0.03em', color:'#fff', lineHeight:1.05, marginBottom:'24px' }}>
              No API keys.<br />No cloud.<br /><span style={{ color:'#52525B' }}>No limits.</span>
            </h2>
            <p data-reveal="up" style={{ fontSize:'17px', color:'#A1A1AA', lineHeight:1.7, marginBottom:'40px', maxWidth:'420px' }}>
              Cortex runs entirely on your machine using AST parsing, graph analysis, and Neo4j. No OpenAI. No Gemini. No keys that expire. No monthly bill.
            </p>
            <div data-stagger style={{ display:'flex', flexDirection:'column', gap:'12px' }}>
              {['Works completely offline','Runs on your own machine','Unlimited repository analysis','No usage costs ever'].map((text) => (
                <div key={text} style={{ display:'flex', alignItems:'center', gap:'12px', fontSize:'15px', color:'#A1A1AA' }}>
                  <span style={{ color:'#34D399', fontSize:'16px' }}>✓</span>{text}
                </div>
              ))}
            </div>
          </div>
          <div data-reveal="right">
            <div style={{ background:'#0A0A0A', border:'1px solid rgba(255,255,255,0.08)', borderRadius:'20px', overflow:'hidden', boxShadow:'0 40px 80px rgba(0,0,0,0.7)' }}>
              <div style={{ background:'#111', borderBottom:'1px solid rgba(255,255,255,0.06)', padding:'12px 16px', display:'flex', alignItems:'center', gap:'8px' }}>
                <div style={{ width:10, height:10, borderRadius:'50%', background:'#FF5F57' }} />
                <div style={{ width:10, height:10, borderRadius:'50%', background:'#FFBD2E' }} />
                <div style={{ width:10, height:10, borderRadius:'50%', background:'#28C840' }} />
                <span style={{ marginLeft:'12px', fontSize:'12px', color:'#52525B', fontFamily:'monospace' }}>cortex.app/dashboard</span>
              </div>
              <div style={{ display:'grid', gridTemplateColumns:'180px 1fr', minHeight:'280px' }}>
                <div style={{ background:'#0D0D0D', borderRight:'1px solid rgba(255,255,255,0.05)', padding:'16px' }}>
                  <div style={{ fontSize:'9px', color:'#52525B', letterSpacing:'0.12em', textTransform:'uppercase', marginBottom:'12px' }}>Recent Jobs</div>
                  {[{name:'DoseBuddy',status:'● done',color:'#34D399'},{name:'VisionAid',status:'◌ run',color:'#FB923C'},{name:'Cortex',status:'● done',color:'#34D399'}].map(({ name, status, color }) => (
                    <div key={name} style={{ padding:'8px 10px', borderRadius:'8px', marginBottom:'4px', background: name==='DoseBuddy' ? 'rgba(124,58,237,0.1)' : 'transparent', borderLeft: name==='DoseBuddy' ? '2px solid #7C3AED' : '2px solid transparent', display:'flex', justifyContent:'space-between' }}>
                      <span style={{ fontSize:'12px', color:'#A1A1AA' }}>{name}</span>
                      <span style={{ fontSize:'10px', color }}>{status}</span>
                    </div>
                  ))}
                </div>
                <div style={{ padding:'20px' }}>
                  <div style={{ fontSize:'14px', fontWeight:500, color:'#fff', marginBottom:'4px' }}>DoseBuddy</div>
                  <div style={{ fontSize:'11px', color:'#52525B', marginBottom:'16px' }}>Architecture Diagram</div>
                  <div style={{ background:'#111', borderRadius:'10px', padding:'14px', fontFamily:'monospace', fontSize:'11px', color:'#52525B', lineHeight:1.9, border:'1px solid rgba(255,255,255,0.04)' }}>
                    <span style={{ color:'#A78BFA' }}>graph</span> <span style={{ color:'#22D3EE' }}>LR</span><br />
                    {'  '}A[API] <span style={{ color:'#34D399' }}>{'-->'}</span> B[Service]<br />
                    {'  '}B <span style={{ color:'#34D399' }}>{'-->'}</span> C[(DB)]
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 6: TECH STACK TICKER ── */}
      <section id="tech-stack" style={{ padding:'80px 0', background:'#000', borderTop:'1px solid rgba(255,255,255,0.04)', borderBottom:'1px solid rgba(255,255,255,0.04)' }}>
        <div data-reveal="up" style={{ fontSize:'11px', fontWeight:500, letterSpacing:'0.16em', textTransform:'uppercase', color:'#52525B', textAlign:'center', marginBottom:'40px' }}>Built with</div>
        <div className="ticker-wrap">
          <div className="ticker-track">
            {[
              'Next.js 14','TypeScript','FastAPI','Python 3.12','Neo4j 5','PostgreSQL 16',
              'Celery 5','Redis 7','React Flow','Docker','SQLAlchemy 2','Pydantic v2',
              'Alembic','Uvicorn','Structlog','Tailwind CSS',
              'Next.js 14','TypeScript','FastAPI','Python 3.12','Neo4j 5','PostgreSQL 16',
              'Celery 5','Redis 7','React Flow','Docker','SQLAlchemy 2','Pydantic v2',
              'Alembic','Uvicorn','Structlog','Tailwind CSS',
            ].map((tech, i) => (
              <div key={i} style={{ display:'inline-flex', alignItems:'center', padding:'10px 22px', border:'1px solid rgba(255,255,255,0.07)', borderRadius:'100px', fontSize:'13px', color:'#71717A', background:'rgba(255,255,255,0.02)', whiteSpace:'nowrap', flexShrink:0, transition:'all 0.2s', cursor:'default' }}
                onMouseEnter={(e) => { e.currentTarget.style.color='#fff'; e.currentTarget.style.borderColor='rgba(255,255,255,0.2)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.color='#71717A'; e.currentTarget.style.borderColor='rgba(255,255,255,0.07)'; }}
              >{tech}</div>
            ))}
          </div>
        </div>
      </section>

      {/* ── SECTION 7: FINAL CTA ── */}
      <section className="section-full" style={{ background:'#000', textAlign:'center', position:'relative', overflow:'hidden' }}>
        <div style={{ position:'absolute', width:'800px', height:'800px', borderRadius:'50%', background:'radial-gradient(circle,rgba(124,58,237,0.08),transparent 70%)', filter:'blur(60px)', top:'50%', left:'50%', transform:'translate(-50%,-50%)', animation:'pulse-glow 8s ease-in-out infinite', pointerEvents:'none' }} />
        <div className="content-max" style={{ position:'relative', zIndex:1, display:'flex', flexDirection:'column', alignItems:'center' }}>
          <div data-reveal="up" style={{ fontSize:'11px', fontWeight:500, letterSpacing:'0.16em', textTransform:'uppercase', color:'#52525B', marginBottom:'32px' }}>Ready?</div>
          <h2 data-reveal="up" style={{ fontSize:'clamp(48px,8vw,104px)', fontWeight:200, letterSpacing:'-0.04em', lineHeight:0.92, color:'#fff', marginBottom:'32px' }}>
            Start analyzing.<br />
            <span className="gradient-text">Start learning.</span>
          </h2>
          <p data-reveal="up" style={{ fontSize:'18px', color:'#71717A', maxWidth:'440px', lineHeight:1.7, marginBottom:'48px' }}>
            Paste your first GitHub URL and see your codebase differently. It takes 30 seconds.
          </p>
          <div data-reveal="up">
            <Link href="/dashboard" style={{ display:'inline-flex', alignItems:'center', gap:'10px', background:'#7C3AED', color:'#fff', fontSize:'16px', fontWeight:500, padding:'16px 36px', borderRadius:'14px', textDecoration:'none', transition:'all 0.25s' }}
              onMouseEnter={(e) => { e.currentTarget.style.background='#6D28D9'; e.currentTarget.style.boxShadow='0 12px 40px rgba(124,58,237,0.5)'; e.currentTarget.style.transform='translateY(-3px) scale(1.02)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background='#7C3AED'; e.currentTarget.style.boxShadow='none'; e.currentTarget.style.transform='translateY(0) scale(1)'; }}
            >Analyze a Repository <span style={{ fontSize:'20px' }}>→</span></Link>
          </div>
          <div data-reveal="up" style={{ marginTop:'48px', fontSize:'13px', color:'#52525B', display:'flex', alignItems:'center', gap:'16px' }}>
            <span>Open source</span>
            <span style={{ color:'#27272A' }}>·</span>
            <span>MIT License</span>
            <span style={{ color:'#27272A' }}>·</span>
            <a href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
              style={{ color:'#52525B', textDecoration:'none' }}
              onMouseEnter={(e) => (e.currentTarget.style.color='#A1A1AA')}
              onMouseLeave={(e) => (e.currentTarget.style.color='#52525B')}
            >Star on GitHub ↗</a>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer style={{ padding:'40px 32px', borderTop:'1px solid rgba(255,255,255,0.06)', background:'#000', display:'flex', justifyContent:'space-between', alignItems:'center', maxWidth:'1200px', margin:'0 auto' }}>
        <div style={{ fontSize:'13px', color:'#52525B' }}>Cortex · Built by Sudheer Kanduru · SRMIST, Chennai · 2025</div>
        <div style={{ display:'flex', gap:'24px' }}>
          {[{label:'GitHub',href:'https://github.com/SUDHEER-KANDURU/cortex'},{label:'Dashboard',href:'/dashboard'}].map(({ label, href }) => (
            <a key={label} href={href} style={{ fontSize:'13px', color:'#52525B', textDecoration:'none', transition:'color 0.2s' }}
              onMouseEnter={(e) => (e.currentTarget.style.color='#A1A1AA')}
              onMouseLeave={(e) => (e.currentTarget.style.color='#52525B')}
            >{label}</a>
          ))}
        </div>
      </footer>

    </main>
  );
}

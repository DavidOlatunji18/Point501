import type { SVGProps } from "react";
import { Mail } from "lucide-react";

// Lucide dropped brand/logo icons a while back, so LinkedIn and Instagram
// are hand-drawn here (standard monochrome glyphs, not the colored brand
// marks) rather than pulling in a whole extra icon package for two icons.
function LinkedInIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
    </svg>
  );
}

function InstagramIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072c-4.358.2-6.78 2.618-6.98 6.98C.014 8.333 0 8.741 0 12s.014 3.667.072 4.948c.2 4.354 2.618 6.782 6.98 6.979C8.333 23.986 8.741 24 12 24s3.667-.014 4.948-.072c4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.667.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z" />
    </svg>
  );
}

export default function Footer() {
  return (
    <footer className="relative border-t border-outline">
      <div className="mx-auto flex h-24 max-w-6xl items-center justify-between px-6">
        <div className="flex items-center gap-2">
          <img src="/Point501_logo_new_cropped.png" alt="Point501 logo" className="h-6 w-auto" />
          <span className="text-sm font-extrabold text-gold">Point501</span>
          <span className="hidden text-sm text-slate-500 sm:inline">
            © {new Date().getFullYear()} All rights reserved.
          </span>
          <span className="text-sm text-slate-500 sm:hidden">© {new Date().getFullYear()}</span>
        </div>

        {/* Links to come once accounts exist */}
        <div className="flex items-center gap-4">
          <a href="#" aria-label="LinkedIn" className="text-slate-400 hover:text-slate-100">
            <LinkedInIcon className="h-5 w-5" />
          </a>
          <a href="#" aria-label="Email" className="text-slate-400 hover:text-slate-100">
            <Mail className="h-5 w-5" />
          </a>
          <a href="#" aria-label="Instagram" className="text-slate-400 hover:text-slate-100">
            <InstagramIcon className="h-5 w-5" />
          </a>
        </div>
      </div>
    </footer>
  );
}

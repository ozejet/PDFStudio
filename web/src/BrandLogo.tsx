type Size=24|40|72;
export function BrandLogo({size=40,className=''}:{size?:Size;className?:string}){
 return <img className={'brand-logo '+className} src={`/branding/pdfstudio-${size}.png`} srcSet={`/branding/pdfstudio-${size*2}.png 2x`} width={size} height={size} alt="" aria-hidden="true" draggable={false} decoding="async"/>;
}

import fitz
from subprocess import run

def recoverpix(doc, item):
    xref = item[0]  # xref of PDF image
    smask = item[1]  # xref of its /SMask

    # special case: /SMask or /Mask exists
    if smask > 0:
        pix0 = fitz.Pixmap(doc.extract_image(xref)["image"])
        if pix0.alpha:  # catch irregular situation
            pix0 = fitz.Pixmap(pix0, 0)  # remove alpha channel
        mask = fitz.Pixmap(doc.extract_image(smask)["image"])

        try:
            pix = fitz.Pixmap(pix0, mask)
        except:  # fallback to original base image in case of problems
            pix = fitz.Pixmap(doc.extract_image(xref)["image"])

        if pix0.n > 3:
            ext = "pam"
        else:
            ext = "png"

        return {  # create dictionary expected by caller
            "ext": ext,
            "colorspace": pix.colorspace.n,
            "image": pix.tobytes(ext),
        }

    # special case: /ColorSpace definition exists
    # to be sure, we convert these cases to RGB PNG images
    if "/ColorSpace" in doc.xref_object(xref, compressed=True):
        pix = fitz.Pixmap(doc, xref)
        pix = fitz.Pixmap(fitz.csRGB, pix)
        return {  # create dictionary expected by caller
            "ext": "png",
            "colorspace": 3,
            "image": pix.tobytes("png"),
        }
    return doc.extract_image(xref)


def extract_images_from_pdf(fname, imgdir, min_width=400, min_height=400, relsize=0.05, abssize=2048, max_ratio=8, max_num=20):
    """
    dimlimit = 0  # 100  # each image side must be greater than this
    relsize = 0  # 0.05  # image : image size ratio must be larger than this (5%)
    abssize = 0  # 2048  # absolute image size limit 2 KB: ignore if smaller
    """
    imgdir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(fname)
    page_count = doc.page_count  # number of pages

    xreflist = []
    imglist = []
    images = []
    for pno in range(page_count):
        if len(images) >= max_num:
            break
        il = doc.get_page_images(pno)
        imglist.extend([x[0] for x in il])
        for img in il:
            xref = img[0]
            if xref in xreflist:
                continue
            width = img[2]
            height = img[3]
            if width < min_width and height < min_height:
                continue
            image = recoverpix(doc, img)
            imgdata = image["image"]

            if len(imgdata) <= abssize:
                continue
            if width / height > max_ratio or height/width > max_ratio:
                continue

            imgname = f'img{pno+1:02}_{xref:05}.{image["ext"]}'
            images.append((imgname, pno+1, width, height))
            with open(imgdir/imgname, "wb") as fout:
                fout.write(imgdata)
            xreflist.append(xref)

    imglist = list(set(imglist))
    return xreflist, imglist, images


def make_md(f, dir_path, summary_dict):
    f.write("\n---\n")
    f.write("<!-- _class: title -->\n")
    f.write(f'# {summary_dict["title_jp"]}\n')
    f.write(f'{summary_dict["title"]}\n')
    f.write(f'[{summary_dict["year"]}] {summary_dict["keywords"]} {summary_dict["entry_id"]}\n\n') 
    f.write(f'__課題__  {summary_dict["problem"]}\n\n')
    f.write(f'__手法__  {summary_dict["method"]}\n\n')
    f.write(f'__結果__  {summary_dict["result"]}\n\n')
    f.write("---\n")
    f.write("<!-- _class: info -->\n") 
    f.write('<span style="font-size: 60%;">\n')
    f.write(summary_dict["abst_jp"].replace("。", "。<br>"))
    f.write("\n</span>")
    f.write("\n\n")
    f.write("---\n")
    f.write("<!-- _class: info -->\n") 
    f.write('<span style="font-size: 60%;">\n')
    f.write(summary_dict["abstract"].replace(". ", ".<br>"))
    f.write("\n</span>")
    f.write("\n\n")

    pdf = summary_dict["pdf"]
    dir_path = dir_path
    
    _, _, image_list = extract_images_from_pdf(pdf, dir_path)
    images = [{"src":imgname, "pno":str(pno), "width":str(width), "height":str(height)} for imgname, pno, width, height in image_list]
    for img in images:
        width = int(img["width"])
        height = int(img["height"])
        x_ratio = (1600.0 * 0.7) / width
        y_ratio = (900.0 * 0.7) / height
        ratio = min(x_ratio, y_ratio)

        f.write("\n---\n")
        f.write("<!-- _class: info -->\n") 
        f.write(f'![width:{int(ratio * width)}]({str(img["src"])})\n')

        
def convert_md_to_pdf(md_file):
    output = md_file.parent / f"{md_file.stem}_slide.pdf"
    cmd = f"marp --pdf --html --allow-local-files {str(md_file)} -o {str(output)} --theme-set marp.css"
    run(cmd, shell=True)
    return output


def make_slides(dir_path, id, summary_dict):
    output = dir_path.resolve() / f"{id}.md"
    with open(output, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write("marp: true\n")
        f.write("theme: default\n")
        f.write("size: 16:9\n")
        f.write("paginate: true\n")
        f.write('_class: ["cool-theme"]\n')
        f.write("\n")

        make_md(f, dir_path, summary_dict)
    output = convert_md_to_pdf(output)
    return output
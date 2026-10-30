import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageOps
import os

class ImageCropperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("自动图片裁剪工具")
        self.root.geometry("400x350")
        
        self.image_path = None
        
        # 标题
        title_label = tk.Label(root, text="自动图片居中裁剪", font=("Arial", 16, "bold"))
        title_label.pack(pady=15)
        
        # 宽设置
        frame_w = tk.Frame(root)
        frame_w.pack(pady=5)
        tk.Label(frame_w, text="目标宽度 (像素):").pack(side=tk.LEFT)
        self.entry_w = tk.Entry(frame_w)
        self.entry_w.pack(side=tk.LEFT, padx=5)
        
        # 高设置
        frame_h = tk.Frame(root)
        frame_h.pack(pady=5)
        tk.Label(frame_h, text="目标高度 (像素):").pack(side=tk.LEFT)
        self.entry_h = tk.Entry(frame_h)
        self.entry_h.pack(side=tk.LEFT, padx=5)
        
        # 导入按钮
        self.btn_import = tk.Button(root, text="1. 导入图片", command=self.import_image, width=20, bg="#e0f7fa")
        self.btn_import.pack(pady=15)
        
        # 状态显示
        self.lbl_status = tk.Label(root, text="当前未导入图片", fg="gray")
        self.lbl_status.pack(pady=5)
        
        # 输出按钮
        self.btn_export = tk.Button(root, text="2. 裁剪并输出图片", command=self.export_image, width=20, bg="#e8f5e9", state=tk.DISABLED)
        self.btn_export.pack(pady=10)

    def import_image(self):
        file_path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif *.webp")]
        )
        if file_path:
            self.image_path = file_path
            filename = os.path.basename(file_path)
            # 获取原图尺寸用于提示
            try:
                with Image.open(file_path) as img:
                    orig_w, orig_h = img.size
                self.lbl_status.config(text=f"已导入: {filename} ({orig_w}x{orig_h})", fg="green")
                self.btn_export.config(state=tk.NORMAL)
            except Exception as e:
                messagebox.showerror("错误", f"无法读取图片信息: {e}")

    def export_image(self):
        if not self.image_path:
            messagebox.showerror("错误", "请先导入图片")
            return
            
        try:
            width = int(self.entry_w.get())
            height = int(self.entry_h.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字宽度和高度")
            return
            
        if width <= 0 or height <= 0:
            messagebox.showerror("错误", "宽度和高度必须大于0")
            return
            
        # 尝试使用原图相同的格式和名字，加上裁剪后缀
        orig_filename = os.path.basename(self.image_path)
        name, ext = os.path.splitext(orig_filename)
        default_save_name = f"{name}_cropped_{width}x{height}{ext}"
        
        save_path = filedialog.asksaveasfilename(
            title="保存图片",
            initialfile=default_save_name,
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("BMP", "*.bmp"), ("WebP", "*.webp"), ("All Files", "*.*")]
        )
        
        if not save_path:
            return
            
        try:
            with Image.open(self.image_path) as img:
                # 使用ImageOps.fit进行自动居中裁剪，保证填充指定的宽高且不变形
                # LANCZOS是高质量的重采样滤波器
                cropped_img = ImageOps.fit(img, (width, height), method=Image.Resampling.LANCZOS)
                
                # 如果保存为jpg且原图是RGBA（带透明通道），需要转换为RGB加白色背景
                save_ext = os.path.splitext(save_path)[1].lower()
                if save_ext in ('.jpg', '.jpeg'):
                    if cropped_img.mode in ('RGBA', 'LA', 'P'):
                        bg = Image.new('RGB', cropped_img.size, (255, 255, 255))
                        if cropped_img.mode == 'P':
                            cropped_img = cropped_img.convert('RGBA')
                        if cropped_img.mode == 'RGBA':
                            bg.paste(cropped_img, mask=cropped_img.split()[3])
                        else:
                            bg.paste(cropped_img, mask=cropped_img.split()[1])
                        cropped_img = bg
                        
                cropped_img.save(save_path)
                messagebox.showinfo("成功", f"图片已成功裁剪并保存到:\n{save_path}")
        except Exception as e:
            messagebox.showerror("错误", f"处理图片时发生错误:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageCropperApp(root)
    root.mainloop()

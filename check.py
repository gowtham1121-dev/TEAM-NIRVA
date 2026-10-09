
import sys, torch, torchvision, cv2, numpy, sklearn, fastapi

print("Python", sys.version.split()[0])
print("torch", torch.__version__, "| GPU available:", torch.cuda.is_available())
print("opencv", cv2.__version__)

x = torch.rand(2000, 2000)
print("matrix test ok", (x @ x).shape)
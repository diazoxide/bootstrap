# Installation

```shell
TD=/usr/local/lib; TF="$TD/bs.zip"; TSD="$TD/bs";\
sudo wget -O "$TF" https://github.com/diazoxide/bootstrap/archive/refs/heads/master.zip\
&& sudo rm -rf "$TSD"\
&& sudo unzip -q "$TF" -d "$TSD"\
&& sudo chmod +x "$TSD/bootstrap-master/bs.py"\
&& sudo rm "/usr/local/bin/bs"\
&& sudo ln -s "$TSD/bootstrap-master/bs.py" /usr/local/bin/bs && echo  -e "\033[92m --- Successfully done. Run 'bs help' to start. --- \033[0m"
```

# Usage

```shell
bs help
```
# chat_app

* docker pull nginx:latest
*  docker run -dt --name nginx-chat 80:80 nginx
*  docker cp streamlit.conf {CONTAINER ID}:/etc/nginx/conf.d/
*  docker exec -ti {CONTAINER ID} bash  && rm /etc/nginx/conf.d/default.conf
*  docker restart {CONTAINER ID}

## start streamlit
nohup streamlit run chat_app.py --server.port 8501 --server.address 0.0.0.0 > streamlit.log 2>&1 &

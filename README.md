# chat_app
1.docker pull nginx:latest
2.docker run -dt --name nginx-chat 80:80 nginx
3.docker cp streamlit.conf {CONTAINER ID}:/etc/nginx/conf.d/
4.docker exec -ti {CONTAINER ID} bash  && rm /etc/nginx/conf.d/default.conf
5.docker restart {CONTAINER ID}


# start streamlit
nohup streamlit run chat_app.py --server.port 8501 --server.address 0.0.0.0 > streamlit.log 2>&1 &
